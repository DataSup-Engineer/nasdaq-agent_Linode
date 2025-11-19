"""
Setup script for NASDAQ Stock Agent
"""
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="nasdaq-stock-agent",
    version="1.0.0",
    description="AI-powered NASDAQ stock analysis and investment recommendations",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "nasdaq-agent=main:main",
        ],
    },
)