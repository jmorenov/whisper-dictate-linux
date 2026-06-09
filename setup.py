from setuptools import setup, find_packages

setup(
    name="whisper-dictate",
    version="1.0.0",
    description="Push-to-talk voice dictation for Linux. 100% offline, powered by whisper.cpp.",
    author="jmorenov",
    url="https://github.com/jmorenov/whisper-dictate-linux",
    packages=find_packages(),
    install_requires=["evdev>=1.9"],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Utilities",
    ],
    license="MIT",
)
