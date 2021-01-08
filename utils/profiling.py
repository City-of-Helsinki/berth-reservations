import cProfile
import functools
import io
import os
import pstats
import sys
import threading
import time

__all__ = [
    "profiling_support",
    "run_with_profiler",
    "profile_call",
    "ProfilingMiddleware",
]


def profiling_support(func):
    """
    run a function with profiler enabled, if BERTH_PROFILING_ENABLED is set to 1 in environment.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if get_profile_flag():
            return profile_call(func, *args, **kwargs)
        else:
            return func(*args, **kwargs)

    return wrapper


def run_with_profiler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return profile_call(func, *args, **kwargs)

    return wrapper


def profile_call(func, *args, **kwargs):
    profile = cProfile.Profile()
    try:
        profile.enable()
        return func(*args, **kwargs)
    finally:
        profile.disable()
        dump_profiling_results(
            profile, f"{func.__name__}-{threading.current_thread().ident}"
        )


def dump_profiling_results(profile, identifier=None):
    s = io.StringIO()
    num_results = int(os.getenv("PROFILE_RESULTS", "100"))
    sortby = os.getenv("PROFILE_SORT", "cumulative")
    for sort_val in sortby.split(","):
        ps = pstats.Stats(profile, stream=s).sort_stats(sort_val)
        ps.print_stats(num_results)

        if os.getenv("PROFILE_CALLEES") == "1":
            ps.print_callees(num_results)

        if os.getenv("PROFILE_CALLERS") == "1":
            ps.print_callers(num_results)

    sys.stderr.write(s.getvalue())

    if identifier is None:
        identifier = ""

    if os.getenv("DUMP_PROFILING_RESULTS") == "1":
        profile.dump_stats(f"/tmp/profile-{time.time()}-{identifier}")


class ProfiledThread(threading.Thread):
    # Overrides threading.Thread.run()
    # NOTE: if overriding Thread.run() in subclass, this does not work.
    def run(self):
        profiler = cProfile.Profile()
        try:
            return profiler.runcall(threading.Thread.run, self)
        finally:
            profiler.dump_stats(f"/tmp/myprofile-{self.ident}.profile")


def get_thread_class():
    if get_profile_flag():
        return ProfiledThread
    else:
        return threading.Thread


def get_profile_flag():
    return os.getenv("BERTH_PROFILING_ENABLED") == "1"


class ProfilingMiddleware:

    PROFILE_MIN_DURATION_SECONDS = float(
        os.getenv("PROFILE_MIN_DURATION_SECONDS", "0.0")
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.is_enabled = get_profile_flag()

    def __call__(self, request):
        if self.is_enabled:
            start_time = time.time()
            profiler = cProfile.Profile()
            profiler.enable()
            response = self.get_response(request)
            if time.time() - start_time >= self.PROFILE_MIN_DURATION_SECONDS:
                profiler.disable()
                dump_profiling_results(profiler, "request")
            return response

        else:
            return self.get_response(request)
