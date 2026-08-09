"""Small off-chain GenLayer harness for the Nomic tests.

It provides just enough of the GenVM surface for the deterministic parts of
the contract to run as ordinary Python: storage containers, sender context,
public decorators, nondeterministic prompt scripting and the equivalence
principle wrapper.
"""

from __future__ import annotations

import copy
import importlib
import json
import pathlib
import sys
import types


class Address(str):
    @property
    def as_hex(self) -> str:
        return str(self)


Address.ZERO = Address("0x" + "00" * 20)


def u32(value: int) -> int:
    value = int(value)
    if value < 0 or value > 2**32 - 1:
        raise ValueError("u32 out of range")
    return value


class DynArray(list):
    @classmethod
    def __class_getitem__(cls, _item):
        return cls


class TreeMap(dict):
    @classmethod
    def __class_getitem__(cls, _item):
        return cls


def allow_storage(cls):
    return cls


class _Message:
    sender_address = Address.ZERO


class _Public:
    @staticmethod
    def write(fn):
        fn._genlayer_write = True
        return fn

    @staticmethod
    def view(fn):
        fn._genlayer_view = True
        return fn


class _Nondet:
    queue = []
    prompts = []

    @classmethod
    def exec_prompt(cls, prompt: str) -> str:
        cls.prompts.append(prompt)
        if not cls.queue:
            raise AssertionError("no scripted nondet output")
        return cls.queue.pop(0)


class _EqPrinciple:
    calls = []

    @classmethod
    def prompt_comparative(cls, fn, principle: str):
        result = fn()
        cls.calls.append({"principle": principle, "result": result})
        return result


class Contract:
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        annotations = {}
        for base in reversed(cls.__mro__):
            annotations.update(getattr(base, "__annotations__", {}))
        for name, typ in annotations.items():
            if typ is DynArray:
                setattr(obj, name, DynArray())
            elif typ is TreeMap:
                setattr(obj, name, TreeMap())
        return obj


class _GL:
    Contract = Contract
    public = _Public()
    message = _Message()
    nondet = _Nondet
    eq_principle = _EqPrinciple


gl = _GL()


def _install_genlayer_stub() -> None:
    mod = types.ModuleType("genlayer")
    for name, value in {
        "Address": Address,
        "DynArray": DynArray,
        "TreeMap": TreeMap,
        "allow_storage": allow_storage,
        "u32": u32,
        "gl": gl,
    }.items():
        setattr(mod, name, value)
    sys.modules["genlayer"] = mod


_install_genlayer_stub()


def verdict_json(verdict: str, rule_id: int, reasoning: str | None = None) -> str:
    return json.dumps(
        {
            "reasoning": reasoning or (verdict + " by rule " + str(rule_id)),
            "verdict": verdict,
            "rule_id": rule_id,
        }
    )


class _Actor:
    def __init__(self, game: "Game", addr: Address):
        self.game = game
        self.addr = addr

    def __getattr__(self, name: str):
        attr = getattr(self.game.c, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            before = copy.deepcopy(self.game.c)
            old_sender = gl.message.sender_address
            gl.message.sender_address = self.addr
            try:
                return attr(*args, **kwargs)
            except Exception:
                if getattr(attr, "_genlayer_write", False):
                    self.game.c = before
                raise
            finally:
                gl.message.sender_address = old_sender

        return call


class Game:
    def __init__(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        contracts = str(root / "contracts")
        if contracts not in sys.path:
            sys.path.insert(0, contracts)
        self.module = importlib.import_module("nomic")
        self.c = self.module.Nomic()
        _Nondet.queue = []

    def by(self, addr: Address) -> _Actor:
        return _Actor(self, addr)

    def script(self, *outputs: str) -> None:
        _Nondet.queue = list(outputs)
