from setuptools import setup, find_packages

index_url = None

install_requires = [
    f"odigos-opentelemetry-python3.8 @ {index_url}" if index_url else "odigos-opentelemetry-python3.8==1.0.68"
]

setup(
    name="odigos-python-configurator",
    version="1.0.68",
    description="Odigos Configurator for Python OpenTelemetry Auto-Instrumentation",
    author="Tamir David",
    author_email="tamir@odigos.io",
    packages=find_packages(include=["configurator", "configurator.*"]),
    install_requires=install_requires,
    python_requires=">=3.8",
    entry_points={
        'opentelemetry_configurator': [
            'odigos-python-configurator = configurator:OdigosPythonConfigurator'
        ],
    },
)
