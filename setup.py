from setuptools import setup, find_packages


setup(
    name="wool",
    version="0.0.0",
    packages=find_packages(),
    install_requires=["black>=18.6b4", "requests>=2.19.1,<3.0.0"],
    package_data={},
    scripts=[],
    entry_points={"console_scripts": ["wool=wool.comment_pr:main"]},
)
