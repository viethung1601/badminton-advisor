"""Shim: the pipeline lives in badminton.data.pipeline.clean_rackets."""
import runpy

if __name__ == "__main__":
    runpy.run_module("badminton.data.pipeline.clean_rackets", run_name="__main__")