import ctypes
import sys
from types import SimpleNamespace
import pytest

from kotoba.global_dictation import WindowsInput, Input, GlobalDictation
from kotoba.speech import Transcript


def test_native_input_structure_has_windows_abi_size():
    if sys.platform == "win32":
        assert ctypes.sizeof(Input) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_changed_target_refuses_paste_before_any_input():
    native = WindowsInput.__new__(WindowsInput)
    native.target = lambda: (102, 2)
    native.api = SimpleNamespace(SendInput=lambda *args: pytest.fail("Wrong window received input"))
    with pytest.raises(RuntimeError, match="Target changed"):
        native.paste((101, 1))


def test_held_modifiers_refuse_paste_before_any_input():
    native = WindowsInput.__new__(WindowsInput)
    native.target = lambda: (101, 1)
    native.api = SimpleNamespace(GetAsyncKeyState=lambda key: 0x8000,
                                SendInput=lambda *args: pytest.fail("Held key was modified"))
    with pytest.raises(RuntimeError, match="Release shortcut"):
        native.paste((101, 1))


def test_uncertain_transcript_keeps_review_boundary():
    messages = []
    controller = GlobalDictation.__new__(GlobalDictation)
    # PySide base objects require initialization even when testing their pure path.
    from PySide6.QtCore import QAbstractNativeEventFilter
    QAbstractNativeEventFilter.__init__(controller)
    controller.target = (101, 1)
    controller.notice = lambda *args: messages.append(args)
    controller.deliver(Transcript("uncertain", "en", 1, (), 1, .1, "fixture", ("low_decoder_score",)))
    assert controller.target is None
    assert messages[0][0] == "Review the transcript in Voice Studio"


def test_async_model_preparation_retains_original_dictation_target():
    from PySide6.QtCore import QAbstractNativeEventFilter
    control = GlobalDictation.__new__(GlobalDictation)
    QAbstractNativeEventFilter.__init__(control)
    control.enabled = True
    control.target = None
    voice = SimpleNamespace(job=None, stream=None, meeting_active=False,
                            audio_source=SimpleNamespace(currentData=lambda: SimpleNamespace(kind="microphone")))
    voice.record = lambda: setattr(voice, "job", object())
    control.voice = voice
    control.native = SimpleNamespace(target=lambda: (101, 2))
    notices = []
    control.notice = lambda *args: notices.append(args)
    control.toggle()
    assert control.target == (101, 2)
    assert notices[-1][0] == "Preparing speech model…"
