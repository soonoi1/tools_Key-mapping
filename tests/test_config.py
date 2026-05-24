import unittest

from key_mapper_sdk.config import parse_config


class ConfigTests(unittest.TestCase):
    def test_parse_default_style_mapping(self):
        config = parse_config(
            {
                "mappings": [
                    {
                        "name": "Side to Alt",
                        "enabled": True,
                        "mode": "hold",
                        "trigger": {"all": ["mouse.x1"]},
                        "target": {"keys": ["alt"]},
                    }
                ]
            }
        )

        self.assertEqual(config.mappings[0].trigger.all, ("mouse.x1",))
        self.assertEqual(config.mappings[0].target.keys, ("alt",))
