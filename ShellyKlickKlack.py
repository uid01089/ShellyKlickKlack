from __future__ import annotations

import logging
from pathlib import Path
import time
import os
from datetime import datetime
import paho.mqtt.client as pahoMqtt
from PythonLib.JsonUtil import JsonUtil
from PythonLib.Mqtt import Mqtt
from PythonLib.DateUtil import DateTimeUtilities
from PythonLib.MqttConfigContainer import MqttConfigContainer
from PythonLib.Scheduler import Scheduler


logger = logging.getLogger('ShellyKlickKlack')

DATA_PATH = Path(os.getenv('DATA_PATH', "."))

CONFIG = {
    "shellies/house/garage/test/relay/0/command":
    {
        "on": "on",
        "off": "off",
        "switchTimeMs": 1000
    }
}


class Module:
    def __init__(self) -> None:
        self.scheduler = Scheduler()
        self.mqttClient = Mqtt("koserver.iot", "/house/agents/ShellyKlickKlack", pahoMqtt.Client("ShellyKlickKlack"))
        self.config = MqttConfigContainer(self.mqttClient, "/house/agents/ShellyKlickKlack/config", DATA_PATH.joinpath("ShellyKlickKlack.json"), CONFIG)

    def getConfig(self) -> MqttConfigContainer:
        return self.config

    def getScheduler(self) -> Scheduler:
        return self.scheduler

    def getMqttClient(self) -> Mqtt:
        return self.mqttClient

    def setup(self) -> None:
        self.scheduler.scheduleEach(self.mqttClient.loop, 500)
        self.scheduler.scheduleEach(self.config.loop, 60000)

    def loop(self) -> None:
        self.scheduler.loop()


class ShellyKlickKlack:

    def __init__(self, module: Module) -> None:
        self.configContainer = module.getConfig()
        self.mqttClient = module.getMqttClient()
        self.scheduler = module.getScheduler()
        self.config = {}

    def setup(self) -> None:

        self.configContainer.setup()
        self.configContainer.subscribeToConfigChange(self.__updateConfig)

        self.mqttClient.subscribeIndependentTopic(f'/house/agents/ShellyKlickKlack/set', self.__receiveData)
        self.scheduler.scheduleEach(self.__keepAlive, 10000)

    def __receiveData(self, payload: str) -> None:

        try:
            topicToSwitch = payload
            configuredSwitches = self.config

            onCommand = configuredSwitches.get(topicToSwitch)['on']
            offCommand = configuredSwitches.get(topicToSwitch)['off']
            switchTimeMs = configuredSwitches.get(topicToSwitch)['switchTimeMs']

            self.mqttClient.publishIndependentTopic(topicToSwitch, str(onCommand))
            self.scheduler.oneShoot(lambda: self.mqttClient.publishIndependentTopic(topicToSwitch, str(offCommand)), switchTimeMs)

        except BaseException:
            logging.exception('')

    def __updateConfig(self, config: dict) -> None:
        self.config = config

    def __keepAlive(self) -> None:
        self.mqttClient.publishIndependentTopic('/house/agents/ShellyKlickKlack/heartbeat', DateTimeUtilities.getCurrentDateString())
        self.mqttClient.publishIndependentTopic('/house/agents/ShellyKlickKlack/subscriptions', JsonUtil.obj2Json(self.mqttClient.getSubscriptionCatalog()))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('ShellyKlickKlack').setLevel(logging.DEBUG)

    module = Module()
    module.setup()

    ShellyKlickKlack(module).setup()

    print("ShellyKlickKlack is running!")

    while (True):
        module.loop()
        time.sleep(0.25)


if __name__ == '__main__':
    main()
