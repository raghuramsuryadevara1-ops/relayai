from setuptools import setup, find_packages

setup(
    name="relayai",
    version="1.0.0",
    description="Claude thinks. Gemini speaks. Save up to 80% on AI API costs.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="RelayAI",
    url="https://github.com/yourusername/relayai",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0",
        "rich>=13.0",
        "anthropic>=0.25.0",
        "google-generativeai>=0.5.0",
        "keyring>=24.0",
        "requests>=2.28",
    ],
    extras_require={
        "oauth": [
            "google-auth-oauthlib>=1.0",
            "google-auth>=2.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "relayai=relayai.cli:cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
