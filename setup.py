#!/usr/bin/env python3
"""
Codex Dreams - Biologically-Inspired Memory Management System
Production Setup Configuration
"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="codex-dreams",
    version="0.4.0",
    author="Codex Dreams Development Team",
    description="A biologically-inspired memory management system with hierarchical episodic memory",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ladvien/codex-dreams",
    packages=find_packages(include=["src*", "biological_memory*", "tests*"]),
    py_modules=["src.codex_service", "src.codex_scheduler", "src.generate_insights"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "black>=24.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
        "test": [
            "pytest>=8.0.0",
            "pytest-cov>=4.0.0",
            "pytest-timeout>=2.2.0",
            "pytest-xdist>=3.5.0",
            "pytest-mock>=3.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "codex=codex_service:main",
            "codex-scheduler=codex_scheduler:main",
            "codex-insights=generate_insights:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
