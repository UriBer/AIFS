#!/usr/bin/env python3
"""Setup script for AIFS local implementation."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aifs",
    version="0.1.0",
    author="AIFS Team",
    author_email="urib@even-derech-it.com",
    description="AI-Native File System (AIFS) - Local Implementation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/UriBer/aifs",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "grpcio",
        "protobuf",
        "grpcio-tools",
        # Removed blake3 to avoid Rust dependency
        "numpy",
        "faiss-cpu",
        "sqlite-utils",
        "pydantic",
        "typer",
        "rich",
    ],
    extras_require={
        "fuse": ["fusepy"],
        "dev": ["pytest", "black", "isort", "mypy"],
    },
    entry_points={
        "console_scripts": [
            "aifs=aifs_cli:app",
        ],
    },
)