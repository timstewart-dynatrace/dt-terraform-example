#!/usr/bin/env python3
"""
Verify that configuration was successfully migrated between tenants.
Compares configuration counts and types between source and target.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Tuple

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Error: Required packages not installed")
    print("Run: pip3 install -r requirements.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationVerifier:
    """Verify successful configuration migration between tenants."""

    def __init__(self, source_url: str, source_token: str,
                 target_url: str, target_token: str):
        """Initialize verifier."""
        self.source_url = source_url.rstrip('/')
        self.target_url = target_url.rstrip('/')
        self.source_token = source_token
        self.target_token = target_token
        self.source_session = self._create_session(source_token)
        self.target_session = self._create_session(target_token)

    def _create_session(self, token: str) -> requests.Session:
        """Create an authenticated requests session."""
        session = requests.Session()
        session.headers.update({'Authorization': f'Api-Token {token}'})
        session.timeout = 15
        return session

    def get_dashboard_count(self, session: requests.Session, url: str) -> Tuple[int, bool]:
        """Get number of dashboards in a tenant."""
        try:
            response = session.get(f'{url}/api/config/v1/dashboards')
            response.raise_for_status()
            dashboards = response.json().get('dashboards', [])
            return len(dashboards), True
        except Exception as e:
            logger.error(f'Error getting dashboards: {e}')
            return -1, False

    def get_alerting_profile_count(self, session: requests.Session, url: str) -> Tuple[int, bool]:
        """Get number of alerting profiles."""
        try:
            response = session.get(f'{url}/api/config/v1/alertingProfiles')
            response.raise_for_status()
            profiles = response.json().get('values', [])
            return len(profiles), True
        except Exception as e:
            logger.error(f'Error getting alerting profiles: {e}')
            return -1, False

    def get_management_zone_count(self, session: requests.Session, url: str) -> Tuple[int, bool]:
        """Get number of management zones."""
        try:
            response = session.get(f'{url}/api/config/v1/managementZones')
            response.raise_for_status()
            zones = response.json().get('values', [])
            return len(zones), True
        except Exception as e:
            logger.error(f'Error getting management zones: {e}')
            return -1, False

    def get_notification_count(self, session: requests.Session, url: str) -> Tuple[int, bool]:
        """Get number of notification configurations."""
        try:
            response = session.get(f'{url}/api/config/v1/notifications')
            response.raise_for_status()
            items = response.json().get('values', [])
            return len(items), True
        except Exception as e:
            logger.error(f'Error getting notifications: {e}')
            return -1, False

    def get_auto_tag_count(self, session: requests.Session, url: str) -> Tuple[int, bool]:
        """Get number of auto-tagging rules."""
        try:
            response = session.get(f'{url}/api/config/v1/autoTags')
            response.raise_for_status()
            tags = response.json().get('values', [])
            return len(tags), True
        except Exception as e:
            logger.error(f'Error getting auto-tags: {e}')
            return -1, False

    def verify(self) -> bool:
        """Run verification checks."""
        logger.info('Starting migration verification...')
        logger.info('=' * 60)

        config_checks = [
            ('Dashboards', self.get_dashboard_count),
            ('Alerting Profiles', self.get_alerting_profile_count),
            ('Management Zones', self.get_management_zone_count),
            ('Notifications', self.get_notification_count),
            ('Auto-Tags', self.get_auto_tag_count),
        ]

        print('\n')
        print(f"{'Configuration':<25} {'Source':<10} {'Target':<10} {'Status':<10}")
        print('-' * 55)

        all_passed = True
        total_source = 0
        total_target = 0

        for name, check_func in config_checks:
            source_count, source_ok = check_func(self.source_session, self.source_url)
            target_count, target_ok = check_func(self.target_session, self.target_url)

            if not source_ok or not target_ok:
                status = 'ERROR'
                all_passed = False
            elif source_count == target_count:
                status = 'PASS'
                total_source += source_count
                total_target += target_count
            elif source_count > 0 and target_count == 0:
                status = 'FAIL'
                all_passed = False
                total_source += source_count
            else:
                status = 'WARN'
                total_source += source_count
                total_target += target_count

            source_display = source_count if source_count >= 0 else 'ERROR'
            target_display = target_count if target_count >= 0 else 'ERROR'

            print(f"{name:<25} {source_display:<10} {target_display:<10} {status:<10}")

        print('-' * 55)
        print(f"{'TOTAL':<25} {total_source:<10} {total_target:<10}")
        print('\n')

        if all_passed:
            logger.info('Verification passed: Migration appears successful')
            return True
        else:
            logger.warning('Verification detected issues: Review counts above')
            return False


def main() -> int:
    """Parse arguments and run verification."""
    parser = argparse.ArgumentParser(
        description='Verify successful Dynatrace configuration migration'
    )

    parser.add_argument('--source', help='Source tenant URL',
                        default=os.getenv('SOURCE_TENANT_URL'))
    parser.add_argument('--target', help='Target tenant URL',
                        default=os.getenv('TARGET_TENANT_URL'))
    parser.add_argument('--source-token', help='Source API token',
                        default=os.getenv('SOURCE_TENANT_TOKEN'))
    parser.add_argument('--target-token', help='Target API token',
                        default=os.getenv('TARGET_TENANT_TOKEN'))

    args = parser.parse_args()

    # Validate arguments
    if not all([args.source, args.target, args.source_token, args.target_token]):
        logger.error('Missing required arguments or environment variables')
        parser.print_help()
        return 1

    try:
        verifier = MigrationVerifier(
            source_url=args.source,
            source_token=args.source_token,
            target_url=args.target,
            target_token=args.target_token
        )

        success = verifier.verify()
        return 0 if success else 1

    except Exception as e:
        logger.error(f'Fatal error: {e}', exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
