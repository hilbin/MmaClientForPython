# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import logging
import unittest
from functools import wraps

from wolframclient.deserializers import binary_deserialize
from wolframclient.evaluation import (WolframKernelPool,
                                      WolframLanguageAsyncSession)
from wolframclient.language import wl
from wolframclient.tests.configure import MSG_JSON_NOT_FOUND, json_config
from wolframclient.tests.evaluation.test_kernel import \
    TestCaseSettings as TestKernelBase
from wolframclient.utils.api import asyncio, time
from wolframclient.utils.tests import TestCase as BaseTestCase

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

loop = asyncio.get_event_loop()


def run_in_loop(cor):
    @wraps(cor)
    def wrapped(*args, **kwargs):
        loop.run_until_complete(cor(*args, **kwargs))

    return wrapped


@unittest.skipIf(json_config is None, MSG_JSON_NOT_FOUND)
class TestCoroutineSession(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.KERNEL_PATH = json_config['kernel']
        cls.setupKernelSession()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownKernelSession()

    @classmethod
    def tearDownKernelSession(cls):
        if cls.async_session is not None:
            cls.async_session.terminate()

    @classmethod
    def setupKernelSession(cls):
        cls.async_session = WolframLanguageAsyncSession(
            cls.KERNEL_PATH, kernel_loglevel=logging.INFO)
        cls.async_session.set_parameter('STARTUP_READ_TIMEOUT', 5)
        cls.async_session.set_parameter('TERMINATE_READ_TIMEOUT', 3)
        cls.async_session.start()

    @run_in_loop
    async def test_eval_inputform(self):
        start = time.perf_counter()
        task = asyncio.ensure_task(
            self.async_session.evaluate('Pause[.1]; Range[3]'))
        timer = time.perf_counter() - start
        self.assertTrue(timer < .1)
        res = await task
        self.assertEqual(res, [1, 2, 3])

    @run_in_loop
    async def test_eval_wlsymbol(self):
        start = time.perf_counter()
        task = asyncio.ensure_task(
            self.async_session.evaluate(
                wl.CompoundExpression(wl.Pause(.1), wl.Range(2))))
        timer = time.perf_counter() - start
        self.assertTrue(timer < .1)
        res = await task
        self.assertEqual(res, [1, 2])

    @run_in_loop
    async def test_eval_wxf(self):
        start = time.perf_counter()
        task = asyncio.ensure_task(
            self.async_session.evaluate_wxf('Pause[.1]; Range[3]'))
        timer = time.perf_counter() - start
        self.assertTrue(timer < .1)
        res = await task
        self.assertEqual(binary_deserialize(res), [1, 2, 3])

    @run_in_loop
    async def test_eval_wrap(self):
        start = time.perf_counter()
        task = asyncio.ensure_task(
            self.async_session.evaluate_wrap('Pause[.1]; Range[3]'))
        timer = time.perf_counter() - start
        self.assertTrue(timer < .1)
        res = await task
        self.assertEqual(res.get(), [1, 2, 3])

    @run_in_loop
    async def test_eval_parallel(self):
        tasks = [
            asyncio.ensure_task(self.async_session.evaluate(i + 1))
            for i in range(10)
        ]
        res = await asyncio.gather(*tasks)
        self.assertEqual(res, list(range(1, 11)))

    def test_kwargs_parameters(self):
        TestKernelBase.class_kwargs_parameters(self,
                                               WolframLanguageAsyncSession)

    def test_bad_kwargs_parameters(self):
        TestKernelBase.class_bad_kwargs_parameters(
            self, WolframLanguageAsyncSession)


@unittest.skipIf(json_config is None, MSG_JSON_NOT_FOUND)
class TestKernelPool(BaseTestCase):
    KERNEL_PATH = json_config['kernel']

    @classmethod
    def setUpClass(cls):
        cls.setupKernelSession()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownKernelSession()

    @classmethod
    def tearDownKernelSession(cls):
        if cls.pool is not None:
            loop.run_until_complete(cls.pool.terminate())

    @classmethod
    def setupKernelSession(cls):
        cls.pool = WolframKernelPool(
            cls.KERNEL_PATH,
            kernel_loglevel=logging.INFO,
            STARTUP_READ_TIMEOUT=5,
            TERMINATE_READ_TIMEOUT=3)
        loop.run_until_complete(cls.pool.start())

    @run_in_loop
    async def test_eval_wlsymbol(self):
        tasks = [
            asyncio.ensure_task(self.pool.evaluate(wl.FromLetterNumber(i)))
            for i in range(1, 11)
        ]
        res = await asyncio.gather(*tasks)
        self.assertEqual({*res},
                         {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"})

    @run_in_loop
    async def test_eval_inputform(self):
        tasks = [
            asyncio.ensure_task(
                self.pool.evaluate('FromLetterNumber[%i]' % i))
            for i in range(1, 11)
        ]
        res = await asyncio.gather(*tasks)
        self.assertEqual({*res},
                         {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"})

    @run_in_loop
    async def test_eval_wxf(self):
        tasks = [
            asyncio.ensure_task(
                self.pool.evaluate_wxf('FromLetterNumber[%i]' % i))
            for i in range(1, 11)
        ]
        res = await asyncio.gather(*tasks)
        res = {binary_deserialize(wxf) for wxf in res}
        self.assertEqual(res,
                         {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"})