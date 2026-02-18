import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
        with open(config_path, 'r') as f:
            self._config = json.load(f)

        self._inject_env_variables()

    def _inject_env_variables(self):

        if 'jasper_vision' not in self._config:
            self._config['jasper_vision'] = {}

        self._config['jasper_vision']['api_key'] = os.getenv(
            'JASPER_API_KEY',
            self._config['jasper_vision'].get('api_key', '')
        )

        self._config['jasper_vision']['domain_id'] = os.getenv(
            'JASPER_DOMAIN_ID',
            self._config['jasper_vision'].get('domain_id', '')
        )

        self._load_data_points_from_env()

    def _load_data_points_from_env(self):
        if 'data_points' not in self._config['jasper_vision']:
            self._config['jasper_vision']['data_points'] = {}

        data_points = self._config['jasper_vision']['data_points']

        data_point_definitions = {
            'ST1_ACTIVE': ('ST1', 'active'),
            'ST1_REACTIVE': ('ST1', 'reactive'),
            'ST2_ACTIVE': ('ST2', 'active'),
            'ST2_REACTIVE': ('ST2', 'reactive'),
            'ST3_ACTIVE': ('ST3', 'active'),
            'ST3_REACTIVE': ('ST3', 'reactive'),
            'ST4_ACTIVE_MASTER': ('ST4', 'active_master'),
            'ST4_REACTIVE_MASTER': ('ST4', 'reactive_master'),
            'ST4_ACTIVE_SLAVE': ('ST4', 'active_slave'),
            'ST4_REACTIVE_SLAVE': ('ST4', 'reactive_slave'),
            'ST5_ACTIVE': ('ST5', 'active'),
            'ST5_REACTIVE': ('ST5', 'reactive'),
            'ST6_ACTIVE': ('ST6', 'active'),
            'ST6_REACTIVE': ('ST6', 'reactive'),
            'ST7_ACTIVE': ('ST7', 'active'),
            'ST7_REACTIVE': ('ST7', 'reactive')
        }

        for env_key, (station, power_type) in data_point_definitions.items():
            env_value = os.getenv(f'JASPER_{env_key}')
            if env_value:
                if station not in data_points:
                    data_points[station] = {}
                data_points[station][power_type] = env_value

    @property
    def database_config(self):
        return self._config['database']

    @property
    def consumption_file(self):
        file_path = self._config['files']['consumption_file']
        return Path(__file__).resolve().parent / file_path

    @property
    def sessions_file(self):
        file_path = self._config['files']['sessions_file']
        return Path(__file__).resolve().parent / file_path

    @property
    def api_host(self):
        return self._config['api']['host']

    @property
    def api_port(self):
        return self._config['api']['port']

    @property
    def cors_origins(self):
        return self._config['api']['cors_origins']

    @property
    def jasper_config(self):
        return self._config['jasper_vision']

    @property
    def data_points(self):
        return self._config['jasper_vision'].get('data_points', {})

settings = Config()