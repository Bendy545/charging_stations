import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        config_path = Path(__file__).resolve().parent.parent / "config.json"
        with open(config_path, 'r') as f:
            self._config = json.load(f)

        self._inject_env_variables()

    def _inject_env_variables(self):
        """Doplní hodnoty z .env souboru do konfigurace"""

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
        """Načte GUID datových bodů z proměnných prostředí"""
        if 'data_points' not in self._config['jasper_vision']:
            self._config['jasper_vision']['data_points'] = {}

        data_points = self._config['jasper_vision']['data_points']

        data_point_definitions = {
            'UR371_ACTIVE': ('UR371', 'active'),
            'UR371_REACTIVE': ('UR371', 'reactive'),
            'UR372_ACTIVE': ('UR372', 'active'),
            'UR372_REACTIVE': ('UR372', 'reactive'),
            'UR367_ACTIVE': ('UR367', 'active'),
            'UR367_REACTIVE': ('UR367', 'reactive'),
            'UR368_ACTIVE_MASTER': ('UR368', 'active_master'),
            'UR368_REACTIVE_MASTER': ('UR368', 'reactive_master'),
            'UR368_ACTIVE_SLAVE': ('UR368', 'active_slave'),
            'UR368_REACTIVE_SLAVE': ('UR368', 'reactive_slave'),
            'UR369_ACTIVE': ('UR369', 'active'),
            'UR369_REACTIVE': ('UR369', 'reactive'),
            'UR370_ACTIVE': ('UR370', 'active'),
            'UR370_REACTIVE': ('UR370', 'reactive'),
            'UR366_ACTIVE': ('UR366', 'active'),
            'UR366_REACTIVE': ('UR366', 'reactive')
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