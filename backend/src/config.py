import json
from pathlib import Path

class Config:
    def __init__(self):
        config_path = Path(__file__).resolve().parent.parent / "config.json"
        with open(config_path, 'r') as f:
            self._config = json.load(f)

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

settings = Config()