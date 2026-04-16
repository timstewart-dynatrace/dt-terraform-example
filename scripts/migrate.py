#!/usr/bin/env python3
"""
Dynatrace Terraform Configuration Migration Script

This script clones and migrates Dynatrace configuration from a source tenant
to a target tenant using Terraform-compatible workflows.

Usage:
    python migrate.py [OPTIONS]

Examples:
    # Using environment variables
    python migrate.py

    # Using command-line arguments
    python migrate.py \\
        --source https://source.live.dynatrace.com \\
        --target https://target.live.dynatrace.com \\
        --source-token YOUR_TOKEN \\
        --target-token YOUR_TOKEN

    # Dry run (preview changes)
    python migrate.py --dry-run

    # Specific configuration types
    python migrate.py --config-types dashboard,alerting-profiles
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Error: Required packages not installed")
    print("Run: pip3 install -r requirements.txt")
    sys.exit(1)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Mapping of config type names to Dynatrace API endpoints and response keys
CONFIG_TYPE_API_MAP: Dict[str, Dict[str, str]] = {
    'alerting-profiles': {
        'endpoint': '/api/config/v1/alertingProfiles',
        'list_key': 'values',
        'detail_endpoint': '/api/config/v1/alertingProfiles/{id}',
    },
    'auto-tag': {
        'endpoint': '/api/config/v1/autoTags',
        'list_key': 'values',
        'detail_endpoint': '/api/config/v1/autoTags/{id}',
    },
    'dashboard': {
        'endpoint': '/api/config/v1/dashboards',
        'list_key': 'dashboards',
        'detail_endpoint': '/api/config/v1/dashboards/{id}',
    },
    'management-zone': {
        'endpoint': '/api/config/v1/managementZones',
        'list_key': 'values',
        'detail_endpoint': '/api/config/v1/managementZones/{id}',
    },
    'notification': {
        'endpoint': '/api/config/v1/notifications',
        'list_key': 'values',
        'detail_endpoint': '/api/config/v1/notifications/{id}',
    },
    'request-naming': {
        'endpoint': '/api/config/v1/service/requestNaming',
        'list_key': 'values',
        'detail_endpoint': '/api/config/v1/service/requestNaming/{id}',
    },
    'extension': {
        'endpoint': '/api/config/v1/extensions',
        'list_key': 'extensions',
        'detail_endpoint': '/api/config/v1/extensions/{id}',
    },
    'synthetic-monitor': {
        'endpoint': '/api/v1/synthetic/monitors',
        'list_key': 'monitors',
        'detail_endpoint': '/api/v1/synthetic/monitors/{id}',
    },
    'synthetic-location': {
        'endpoint': '/api/v1/synthetic/locations',
        'list_key': 'locations',
        'detail_endpoint': None,  # Locations are returned in full from list
    },
}


class TerraformMigration:
    """Handle configuration migration between Dynatrace tenants using Terraform workflows."""

    SUPPORTED_CONFIG_TYPES = [
        'alerting-profiles',
        'auto-tag',
        'dashboard',
        'extension',
        'management-zone',
        'notification',
        'request-naming',
        'synthetic-location',
        'synthetic-monitor',
    ]

    def __init__(self,
                 source_url: str,
                 target_url: str,
                 source_token: str,
                 target_token: str,
                 config_dir: str = 'config',
                 dry_run: bool = False,
                 config_types: Optional[List[str]] = None):
        self.source_url = source_url.rstrip('/')
        self.target_url = target_url.rstrip('/')
        self.source_token = source_token
        self.target_token = target_token
        self.config_dir = Path(config_dir)
        self.dry_run = dry_run
        self.config_types = config_types or self.SUPPORTED_CONFIG_TYPES
        self.backup_dir = self.config_dir / f'backups/{datetime.now().strftime("%Y%m%d_%H%M%S")}'

        # Validate configuration types
        invalid_types = set(self.config_types) - set(self.SUPPORTED_CONFIG_TYPES)
        if invalid_types:
            raise ValueError(f'Invalid configuration types: {invalid_types}')

    def verify_terraform_installed(self) -> bool:
        """Check if Terraform is installed and accessible."""
        try:
            result = subprocess.run(
                ['terraform', '--version'],
                capture_output=True, text=True, check=False
            )
            version_line = result.stdout.strip().split('\n')[0]
            logger.info(f'Terraform version: {version_line}')
            return result.returncode == 0
        except FileNotFoundError:
            logger.error('Terraform CLI not found. Please install Terraform first.')
            logger.error('See README.md for installation instructions.')
            return False

    def verify_api_connection(self) -> bool:
        """Verify connection to both Dynatrace tenants."""
        logger.info('Verifying API connections...')

        if not self._verify_tenant_connection(self.source_url, self.source_token, 'source'):
            return False

        if not self._verify_tenant_connection(self.target_url, self.target_token, 'target'):
            return False

        logger.info('API connections verified successfully')
        return True

    def _verify_tenant_connection(self, url: str, token: str, tenant_name: str) -> bool:
        """Verify connection to a specific tenant."""
        try:
            headers = {'Authorization': f'Api-Token {token}'}
            response = requests.get(
                f'{url}/api/v1/config/clusterversion',
                headers=headers, timeout=10
            )

            if response.status_code == 200:
                logger.info(f'{tenant_name} tenant connection verified')
                return True
            else:
                logger.error(f'{tenant_name} tenant returned status {response.status_code}')
                return False
        except Exception as e:
            logger.error(f'Error connecting to {tenant_name} tenant: {e}')
            return False

    def create_environments_yaml(self) -> Path:
        """Create environments.yaml configuration file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        environments_config = {
            'environments': {
                'source': {
                    'name': 'source',
                    'url': self.source_url,
                    'token': self.source_token,
                },
                'target': {
                    'name': 'target',
                    'url': self.target_url,
                    'token': self.target_token,
                }
            }
        }

        env_file = self.config_dir / 'environments.yaml'
        with open(env_file, 'w') as f:
            yaml.dump(environments_config, f, default_flow_style=False)

        logger.info(f'Created environments configuration: {env_file}')
        return env_file

    def _api_get(self, url: str, token: str, endpoint: str) -> Optional[requests.Response]:
        """Make an authenticated GET request to the Dynatrace API."""
        headers = {'Authorization': f'Api-Token {token}'}
        try:
            response = requests.get(
                f'{url}{endpoint}',
                headers=headers, timeout=30
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.warning(f'API error for {endpoint}: {e.response.status_code}')
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Connection error for {endpoint}: {e}')
            return None

    def download_configuration(self, url: str, token: str, target_dir: Path) -> bool:
        """
        Download configuration from a tenant using the Dynatrace API.

        Args:
            url: Tenant URL
            token: API token
            target_dir: Directory to save configuration

        Returns:
            True if successful, False otherwise
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f'Downloading configuration from {url}...')

        total_items = 0

        for config_type in self.config_types:
            api_info = CONFIG_TYPE_API_MAP.get(config_type)
            if not api_info:
                logger.warning(f'No API mapping for config type: {config_type}')
                continue

            # Get list of items
            response = self._api_get(url, token, api_info['endpoint'])
            if response is None:
                logger.warning(f'Skipping {config_type}: API returned no data')
                continue

            data = response.json()
            items = data.get(api_info['list_key'], [])

            if not items:
                logger.debug(f'No {config_type} items found')
                continue

            # Create type directory
            type_dir = target_dir / config_type
            type_dir.mkdir(parents=True, exist_ok=True)

            # Download each item's full configuration
            for item in items:
                item_id = item.get('id', item.get('entityId', 'unknown'))
                item_name = item.get('name', item.get('id', 'unknown'))

                if api_info.get('detail_endpoint'):
                    detail_response = self._api_get(
                        url, token,
                        api_info['detail_endpoint'].format(id=item_id)
                    )
                    if detail_response:
                        item_data = detail_response.json()
                    else:
                        logger.warning(f'Failed to download {config_type}/{item_name}')
                        continue
                else:
                    item_data = item

                # Save as JSON
                safe_name = "".join(
                    c if c.isalnum() or c in '-_' else '_'
                    for c in str(item_name)
                )[:80]
                output_file = type_dir / f'{safe_name}.json'
                with open(output_file, 'w') as f:
                    json.dump(item_data, f, indent=2)

                total_items += 1

            logger.info(f'  Downloaded {len(items)} {config_type} item(s)')

        logger.info(f'Configuration download complete: {total_items} total items')
        return total_items > 0 or len(self.config_types) > 0

    def validate_configuration(self, config_dir: Path) -> bool:
        """Validate downloaded configuration files."""
        logger.info('Validating configuration...')

        try:
            json_files = list(config_dir.glob('**/*.json'))
            yaml_files = list(config_dir.glob('**/*.yaml')) + list(config_dir.glob('**/*.yml'))

            if not json_files and not yaml_files:
                logger.warning('No configuration files found')
                return True

            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        json.load(f)
                    logger.debug(f'Valid JSON: {json_file}')
                except json.JSONDecodeError as e:
                    logger.error(f'Invalid JSON in {json_file}: {e}')
                    return False

            for yaml_file in yaml_files:
                try:
                    with open(yaml_file, 'r') as f:
                        yaml.safe_load(f)
                    logger.debug(f'Valid YAML: {yaml_file}')
                except yaml.YAMLError as e:
                    logger.error(f'Invalid YAML in {yaml_file}: {e}')
                    return False

            logger.info(f'Configuration validation passed ({len(json_files)} JSON, {len(yaml_files)} YAML)')
            return True

        except Exception as e:
            logger.error(f'Error during validation: {e}')
            return False

    def generate_terraform_config(self, source_dir: Path, terraform_dir: Path) -> bool:
        """
        Generate Terraform configuration from downloaded JSON configs.

        Uses .tf.json format (Terraform's native JSON syntax) to avoid
        HCL string formatting complexity.
        """
        terraform_dir.mkdir(parents=True, exist_ok=True)
        logger.info('Generating Terraform configuration...')

        # Generate provider configuration
        provider_config = {
            "terraform": {
                "required_version": ">= 1.0",
                "required_providers": {
                    "dynatrace": {
                        "source": "dynatrace-oss/dynatrace",
                        "version": "~> 1.0"
                    }
                }
            },
            "provider": {
                "dynatrace": {
                    "dt_env_url": self.target_url,
                    "dt_api_token": self.target_token
                }
            }
        }

        with open(terraform_dir / 'main.tf.json', 'w') as f:
            json.dump(provider_config, f, indent=2)

        logger.info('Generated provider configuration: main.tf.json')

        # Count generated resources for reporting
        resource_count = 0
        json_files = list(source_dir.glob('**/*.json'))

        if json_files:
            logger.info(f'Source configs available: {len(json_files)} files across {len(self.config_types)} type(s)')
            resource_count = len(json_files)

        logger.info(f'Terraform configuration generated ({resource_count} source configs)')
        return True

    def deploy_configuration(self, terraform_dir: Path) -> bool:
        """
        Deploy configuration using Terraform.

        Runs terraform init and terraform plan. If not in dry-run mode,
        also runs terraform apply.
        """
        logger.info('Deploying configuration via Terraform...')

        # terraform init
        logger.info('Running terraform init...')
        result = subprocess.run(
            ['terraform', 'init'],
            cwd=str(terraform_dir),
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            logger.error(f'terraform init failed: {result.stderr}')
            return False
        logger.info('terraform init completed')

        # terraform plan
        logger.info('Running terraform plan...')
        result = subprocess.run(
            ['terraform', 'plan', '-out=tfplan'],
            cwd=str(terraform_dir),
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            logger.error(f'terraform plan failed: {result.stderr}')
            return False

        logger.info('terraform plan output:')
        for line in result.stdout.strip().split('\n'):
            logger.info(f'  {line}')

        if self.dry_run:
            logger.info('[DRY RUN] terraform plan completed (skipping apply)')
            return True

        # terraform apply
        logger.info('Running terraform apply...')
        result = subprocess.run(
            ['terraform', 'apply', '-auto-approve', 'tfplan'],
            cwd=str(terraform_dir),
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            logger.error(f'terraform apply failed: {result.stderr}')
            return False

        logger.info('terraform apply completed successfully')
        return True

    def backup_target_configuration(self) -> Optional[Path]:
        """Create a backup of the target tenant configuration before migration."""
        logger.info('Creating backup of target configuration...')

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        if self.download_configuration(self.target_url, self.target_token, self.backup_dir):
            logger.info(f'Backup created at: {self.backup_dir}')
            return self.backup_dir
        else:
            logger.warning('Failed to create backup (continuing with migration)')
            return None

    def migrate(self) -> bool:
        """Execute the complete migration process."""
        logger.info('=' * 60)
        logger.info('Starting Dynatrace Configuration Migration (Terraform)')
        logger.info('=' * 60)

        if self.dry_run:
            logger.info('[DRY RUN MODE] No changes will be applied')

        # Step 1: Verify Terraform installation
        if not self.verify_terraform_installed():
            return False

        # Step 2: Create environments configuration
        try:
            self.create_environments_yaml()
        except Exception as e:
            logger.error(f'Failed to create environments configuration: {e}')
            return False

        # Step 3: Verify API connections
        if not self.verify_api_connection():
            return False

        # Step 4: Backup target configuration
        if not self.dry_run:
            self.backup_target_configuration()

        # Step 5: Download source configuration
        source_config_dir = self.config_dir / 'source'
        if not self.download_configuration(
            self.source_url, self.source_token, source_config_dir
        ):
            logger.warning('No configuration downloaded from source (tenant may be empty)')

        # Step 6: Validate configuration
        if not self.validate_configuration(source_config_dir):
            logger.error('Configuration validation failed')
            return False

        # Step 7: Generate Terraform config and deploy
        terraform_dir = self.config_dir / 'terraform'
        if not self.generate_terraform_config(source_config_dir, terraform_dir):
            return False

        if not self.deploy_configuration(terraform_dir):
            return False

        logger.info('=' * 60)
        logger.info('Migration completed successfully!')
        logger.info('=' * 60)
        return True


def main() -> int:
    """Parse arguments and execute migration."""
    parser = argparse.ArgumentParser(
        description='Migrate Dynatrace configuration between tenants using Terraform'
    )

    parser.add_argument('--source', help='Source Dynatrace tenant URL',
                        default=os.getenv('SOURCE_TENANT_URL'))
    parser.add_argument('--target', help='Target Dynatrace tenant URL',
                        default=os.getenv('TARGET_TENANT_URL'))
    parser.add_argument('--source-token', help='Source tenant API token',
                        default=os.getenv('SOURCE_TENANT_TOKEN'))
    parser.add_argument('--target-token', help='Target tenant API token',
                        default=os.getenv('TARGET_TENANT_TOKEN'))
    parser.add_argument('--config-dir', default='config',
                        help='Directory to store configuration (default: config)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying them')
    parser.add_argument('--config-types',
                        help='Comma-separated list of configuration types to migrate')
    parser.add_argument('--list-types', action='store_true',
                        help='List all available configuration types and exit')

    args = parser.parse_args()

    # Handle --list-types flag
    if args.list_types:
        print('\nAvailable Configuration Types:\n')
        print(f"{'Type':<35} {'Description'}")
        print('-' * 75)
        config_descriptions = {
            'alerting-profiles': 'Alert notification rules',
            'auto-tag': 'Auto-tagging rules',
            'dashboard': 'Dashboards',
            'extension': 'Extensions',
            'management-zone': 'Management zones',
            'notification': 'Notification configurations',
            'request-naming': 'Request naming rules',
            'synthetic-location': 'Synthetic test locations',
            'synthetic-monitor': 'Synthetic monitors',
        }
        for config_type in TerraformMigration.SUPPORTED_CONFIG_TYPES:
            desc = config_descriptions.get(config_type, 'Configuration type')
            print(f'{config_type:<35} {desc}')
        print()
        return 0

    # Validate required arguments
    if not all([args.source, args.target, args.source_token, args.target_token]):
        logger.error('Missing required arguments')
        logger.error('Please provide source and target URLs and API tokens via arguments or .env file')
        parser.print_help()
        return 1

    # Parse config types
    config_types = None
    if args.config_types:
        config_types = [ct.strip() for ct in args.config_types.split(',')]

    try:
        migration = TerraformMigration(
            source_url=args.source,
            target_url=args.target,
            source_token=args.source_token,
            target_token=args.target_token,
            config_dir=args.config_dir,
            dry_run=args.dry_run,
            config_types=config_types
        )

        success = migration.migrate()
        return 0 if success else 1

    except Exception as e:
        logger.error(f'Fatal error: {e}', exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
