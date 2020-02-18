import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ir_webstats-Tonydatigerr", # Replace with your own username
    version="0.0.1",
    author="jeysonmc",
    author_email="josh.lol1995@gmail.com",
    description="iRacing python client interface to access drivers and series stats and results.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Seattle-iRacing/ir_webstats",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)