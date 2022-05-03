#!/usr/bin/env python3

import requests
import voluptuous as vol
from datetime import datetime, date, timedelta
import urllib.error
from time import time
import urllib.parse
import hashlib
import hmac
import json
import numpy as np

from .const import (
    _LOGGER,
    CONF_ID,
    CONF_KEY,
    CONF_SECRET,
    CONF_UPDATE_FREQUENCY,
    SENSOR_PREFIX,
    COINSPOT_API_ENDPOINT,
)

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_RESOURCES
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_KEY): cv.string,
        vol.Required(CONF_SECRET): cv.string,
        vol.Required(CONF_UPDATE_FREQUENCY, default=60): cv.string,
        vol.Optional(CONF_ID, default=""): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    _LOGGER.debug("Setup coinspot sensor")

    id_name = config.get(CONF_ID)
    key = config.get(CONF_KEY).strip()
    secret = config.get(CONF_SECRET).strip()
    update_frequency = timedelta(minutes=(int(config.get(CONF_UPDATE_FREQUENCY))))

    entities = []

    try:
        entities.append(
            COINSPOTInfoSensor(
                key, secret, update_frequency, id_name
            )
        )
    except urllib.error.HTTPError as error:
        _LOGGER.error(error.reason)
        return False

    add_entities(entities)


class COINSPOTInfoSensor(Entity):
    def __init__(
            self, key, secret, update_frequency, id_name
    ):
        self.data = None
        self.key = key
        self.secret = secret
        self.update = Throttle(update_frequency)(self._update)
        self._name = SENSOR_PREFIX + (id_name + " " if len(id_name) > 0 else "") + key
        self._icon = "mdi:diamond-outline"
        self._totalBalanceInAud = None

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._totalBalanceInAud

    @property
    def extra_state_attributes(self):
        return { 'totalBalanceInAUD': self._totalBalanceInAud }

    def _update(self):
        balances_url = (
                COINSPOT_API_ENDPOINT
                + "/my/balances"
        )

        #_LOGGER.warning("Getting " + balances_url)
        #LOGGER.warning("secret " + self.secret)
        #_LOGGER.warning("key " + self.key)

        payload = {
            'nonce': int(time() * 1000),
        }

        paybytes = json.dumps(payload).replace(' ', '').encode('utf8')
        #_LOGGER.warning(paybytes)

        sign = hmac.new(bytes(self.secret, 'utf8'), paybytes, hashlib.sha512).hexdigest()
        #_LOGGER.warning(sign)

        headers = {
            'key': self.key,
            'sign': sign,
            'Content-Type': 'application/json',
        }
        #_LOGGER.warning(json.dumps(headers).encode('utf8'))


        r = requests.post(balances_url, headers=headers, data=paybytes).json()
        #print(r)
        self.data = r
        
        try:
            if r['status'] != 'ok':
                _LOGGER.error(r['status'])
                raise ValueError()
            else:
                # Set the values of the sensor
                _LOGGER.warning('status ok')
                balances = r['balances']
                _LOGGER.warning('values' + list(balances[0].values())[0].audbalance)
                totalBalance = sum((list(coin.values())[0].audbalance for coin in balances), 0)
                _LOGGER.warning("totalBalance = " + totalBalance)

                self._last_update = datetime.today().strftime("%d-%m-%Y %H:%M")
                self._totalBalanceInAud = 0

        except ValueError:
            self._totalBalanceInAud = 0
            self._last_update = datetime.today().strftime("%d-%m-%Y %H:%M")
