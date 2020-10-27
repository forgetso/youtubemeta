import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ytchannel", # Replace with your own username
    version="0.0.1",
    author="Chris Taylor",
    description="Download YouTube channel data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Creative Commons :: CC0 1.0 Universal",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)