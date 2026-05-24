import unittest

from pynput import keyboard, mouse

from key_mapper_sdk.remapper import key_to_token, mouse_button_to_token, resolve_key


class RemapperTests(unittest.TestCase):
    def test_mouse_side_buttons_are_supported(self):
        self.assertEqual(mouse_button_to_token(mouse.Button.x1), "mouse.x1")
        self.assertEqual(mouse_button_to_token(mouse.Button.x2), "mouse.x2")

    def test_key_aliases_resolve_to_pynput_keys(self):
        self.assertEqual(resolve_key("alt"), keyboard.Key.alt)
        self.assertEqual(resolve_key("key.a"), "a")

    def test_keyboard_tokens_are_normalized(self):
        self.assertEqual(key_to_token(keyboard.Key.alt), "alt")
        self.assertEqual(key_to_token(keyboard.KeyCode.from_char("A")), "a")
