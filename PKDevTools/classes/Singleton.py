#!/usr/bin/python3
"""
The MIT License (MIT)

Copyright (c) 2023 pkjmesra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""


class SingletonType(type):
    def __new__(mcs, name, bases, attrs):
        # Assume the target class is created (i.e. this method to be called) in
        # the main thread.
        cls = super(SingletonType, mcs).__new__(mcs, name, bases, attrs)
        from multiprocessing import Lock

        try:
            cls.__shared_instance_lock__ = Lock()
        except BlockingIOError as e:
            print(f"BlockingIOError: {e}")

        return cls

    def __call__(self, *args, **kwargs):
        with self.__shared_instance_lock__:
            try:
                return self.__shared_instance__
            except AttributeError:
                self.__shared_instance__ = super(SingletonType, self).__call__(
                    *args, **kwargs
                )
                self.__shared_instance__.attributes = {}
                self.__shared_instance__.attributes["lock"] = (
                    self.__shared_instance_lock__
                )
                return self.__shared_instance__


class SingletonMixin:
    def __getstate__(self):
        return getattr(self.__class__, "attributes", {}), self.__dict__

    def __setstate__(self, state):
        attributes, __dict__ = state
        self.__dict__.update(__dict__)
        self.__class__.attributes = attributes


# from multiprocessing.dummy import Pool as ThreadPool
# from threading import get_ident
# from __future__ import absolute_import, division, print_function, unicode_literals
# from multiprocessing.dummy import Pool as ThreadPool
# class NonThreadSafeSingletonType(type):
#     def __call__(cls, *args, **kwargs):
#         try:
#             return cls.__shared_instance__
#         except AttributeError:
#             cls.__shared_instance__ = super(NonThreadSafeSingletonType, cls).__call__(*args, **kwargs)
#             return cls.__shared_instance__


# def run(DatabaseClass):
#     result_set = set()
#     result_set_access_lock = Lock()

#     def worker(_result_set, _result_set_access_lock):
#         db = DatabaseClass()
#         with _result_set_access_lock:
#             _result_set.add(db)

#     thread_pool = ThreadPool(10)
#     for i in six.moves.range(100):
#         thread_pool.apply_async(worker, (result_set, result_set_access_lock))
#     thread_pool.close()
#     thread_pool.join()

#     print(result_set)
#     print(len(result_set))


# if __name__ == "__main__":
#     import six


#     class DatabaseBase(object):
#         def __init__(self):
#             super(DatabaseBase, self).__init__()
#             print("Created in thread: {}".format(get_ident()))

#         def __repr__(self):
#             return "<A database>"


#     @six.add_metaclass(SingletonType)
#     class Database(DatabaseBase):
#         pass


#     @six.add_metaclass(NonThreadSafeSingletonType)
#     class NonThreadSafeDatabase(DatabaseBase):
#         pass


#     class NonSingletonDatabase(DatabaseBase):
#         pass


#     print("Thread-safe Singleton =============================")
#     run(Database)
#     print("Thread-safe Singleton =============================\n\n")

#     print("Non-Thread-safe Singleton =========================")
#     run(NonThreadSafeDatabase)
#     print("Non-Thread-safe Singleton =========================\n\n")

#     print("Normal ============================================")
#     run(NonSingletonDatabase)
#     print("Normal ============================================\n\n")
