from setuptools import find_packages
from setuptools import setup

setup(
  name = 'gitPrice',
  version = '1.0.0',
  description = 'Uses git log to calculate the price of code from an hourly rate.',
  author = 'Tayler Porter',
  author_email = 'taylerporter@gmail.com',
  packages = find_packages(),
  entry_points = {
    'console_scripts': [
      'gitPrice = gitPrice.gitPrice:main'
    ]
  }
)

