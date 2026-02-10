"""
Removed package.

The `ypack.web` package has been removed from the core distribution. It
was moved to a top-level package `ypack_web` (see `ypack_web/*`).
Attempting to import this module will raise ImportError to fail-fast
and make migration explicit.
"""

raise ImportError("The `ypack.web` package has been removed. Import `ypack_web` instead.")

