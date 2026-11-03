"""Shim: the pipeline lives in badminton.data.pipeline.build_shoes_db."""
import runpy

if __name__ == "__main__":
    runpy.run_module("badminton.data.pipeline.build_shoes_db", run_name="__main__")