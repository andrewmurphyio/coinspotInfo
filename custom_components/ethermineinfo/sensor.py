#!/usr/bin/env python3

import requests
import voluptuous as vol
from datetime import datetime, date, timedelta
import urllib.error

from .const import (
    _LOGGER,
    CONF_CURRENCY_NAME,
    CONF_ID,
    CONF_MINER_ADDRESS,
    CONF_UPDATE_FREQUENCY,
    CONF_NAME_OVERRIDE,
    SENSOR_PREFIX,
    TWOMINERS_API_ENDPOINT,
    COINGECKO_API_ENDPOINT,
    ATTR_ACTIVE_WORKERS,
    ATTR_CURRENT_HASHRATE,
    ATTR_INVALID_SHARES,
    ATTR_LAST_UPDATE,
    ATTR_REPORTED_HASHRATE,
    ATTR_STALE_SHARES,
    ATTR_UNPAID,
    ATTR_PAID,
    ATTR_VALID_SHARES,
    ATTR_AMOUNT,
    ATTR_TXHASH,
    ATTR_PAID_ON,
    ATTR_SINGLE_COIN_LOCAL_CURRENCY,
    ATTR_TOTAL_UNPAID_LOCAL_CURRENCY,
    ATTR_TOTAL_PAID_LOCAL_CURRENCY,
    ATTR_CURRENT_HASHRATE_MH_SEC
)

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_RESOURCES
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MINER_ADDRESS): cv.string,
        vol.Required(CONF_UPDATE_FREQUENCY, default=1): cv.string,
        vol.Required(CONF_CURRENCY_NAME, default="usd"): cv.string,
        vol.Optional(CONF_ID, default=""): cv.string,
        vol.Optional(CONF_NAME_OVERRIDE, default=""): cv.string
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    _LOGGER.debug("Setup 2minersInfo sensor")

    id_name = config.get(CONF_ID)
    miner_address = config.get(CONF_MINER_ADDRESS).strip()
    local_currency = config.get(CONF_CURRENCY_NAME).strip().lower()
    update_frequency = timedelta(minutes=(int(config.get(CONF_UPDATE_FREQUENCY))))
    name_override = config.get(CONF_NAME_OVERRIDE).strip()

    entities = []

    try:
        entities.append(
            TwoMinersInfoSensor(
                miner_address, local_currency, update_frequency, id_name, name_override
            )
        )
    except urllib.error.HTTPError as error:
        _LOGGER.error(error.reason)
        return False

    add_entities(entities)


class TwoMinersInfoSensor(Entity):
    def __init__(
            self, miner_address, local_currency, update_frequency, id_name, name_override
    ):
        self.data = None
        self.miner_address = miner_address
        self.local_currency = local_currency
        self.update = Throttle(update_frequency)(self._update)
        if name_override:
            self._name = SENSOR_PREFIX + name_override
        else:
            self._name = SENSOR_PREFIX + (id_name + " " if len(id_name) > 0 else "") + miner_address
        self._icon = "mdi:ethereum"
        self._state = None
        self._active_workers = None
        self._current_hashrate = None
        self._invalid_shares = None
        self._last_update = None
        self._reported_hashrate = None
        self._stale_shares = None
        self._unpaid = None
        self._paid = None
        self._valid_shares = None
        self._unit_of_measurement = "\u200b"
        self._amount = None
        self._txhash = None
        self._paid_on = None
        self._single_coin_in_local_currency = None
        self._unpaid_in_local_currency = None
        self._paid_in_local_currency = None
        self._current_hashrate_mh_sec = None


    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def extra_state_attributes(self):
        return {ATTR_ACTIVE_WORKERS: self._active_workers, ATTR_CURRENT_HASHRATE: self._current_hashrate,
                ATTR_INVALID_SHARES: self._invalid_shares, ATTR_LAST_UPDATE: self._last_update,
                ATTR_REPORTED_HASHRATE: self._reported_hashrate, ATTR_STALE_SHARES: self._stale_shares,
                ATTR_UNPAID: self._unpaid, ATTR_PAID: self._paid, ATTR_VALID_SHARES: self._valid_shares,
                ATTR_AMOUNT: self._amount, ATTR_TXHASH: self._txhash,
                ATTR_PAID_ON: self._paid_on, 
                ATTR_SINGLE_COIN_LOCAL_CURRENCY: self._single_coin_in_local_currency,
                ATTR_TOTAL_UNPAID_LOCAL_CURRENCY: self._unpaid_in_local_currency,
                ATTR_TOTAL_PAID_LOCAL_CURRENCY: self._paid_in_local_currency,
                ATTR_CURRENT_HASHRATE_MH_SEC: self._current_hashrate_mh_sec }

    def _update(self):
        accounts_url = (
                TWOMINERS_API_ENDPOINT
                + self.miner_address
        )

        coingeckourl = (
                COINGECKO_API_ENDPOINT
                + self.local_currency
        )

        #_LOGGER.warning("Getting " + accounts_url)
        # sending get request to 2miners dashboard endpoint
        r = requests.get(accounts_url).json()
        #_LOGGER.warning("Got " + r)
        # extracting response json
        self.data = r
        
        #_LOGGER.warning("Getting " + coingeckourl)
        # sending get request to Congecko API endpoint
        r4 = requests.get(url=coingeckourl).json()
        #_LOGGER.warning("Got " + r4)
        # extracting response json
        self.data4 = r4
        
        try:
            if len(r['workers']) == 0:
                raise ValueError()
            if len(r['workers']) >= 1:
                # Set the values of the sensor
                self._last_update = datetime.today().strftime("%d-%m-%Y %H:%M")
                self._state = r['workersOnline']
                # set the attributes of the sensor
                self._active_workers = r['workersOnline']
                self._current_hashrate = r['currentHashrate']
                self._invalid_shares = r['sharesInvalid']
                self._reported_hashrate = r['hashrate']
                self._stale_shares = r['sharesStale']
                self._unpaid = r['stats']['balance'] / 1000000000
                self._paid = r['stats']['paid'] / 1000000000
                self._valid_shares = r['sharesValid']
                calculate_hashrate_mh_sec = self._current_hashrate / 1000000
                self._current_hashrate_mh_sec = round(calculate_hashrate_mh_sec, 2)
                if len(r['payments']):
                    self._amount = r['payments'][0]['amount'] / 1000000000
                    self._txhash = r['payments'][0]['tx']
                    self._paid_on = datetime.fromtimestamp(int(r['payments'][0]['timestamp'])).strftime(
                        '%d-%m-%Y %H:%M')
                if len(r4['ethereum']):
                    self._single_coin_in_local_currency = r4['ethereum'][self.local_currency]
                    calculate_unpaid = self._unpaid * self._single_coin_in_local_currency
                    self._unpaid_in_local_currency = round(calculate_unpaid,2)
                    calculate_paid = self._paid * self._single_coin_in_local_currency
                    self._paid_in_local_currency = round(calculate_paid,2)
            else:
                raise ValueError()

        except ValueError:
            self._state = 0
            self._active_workers = 0
            self._last_update = datetime.today().strftime("%d-%m-%Y %H:%M")
