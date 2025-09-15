"""Simplified AWS Athena client for Common Crawl queries."""

import logging
import re
from typing import List, Optional

import boto3
from botocore.exceptions import NoCredentialsError, BotoCoreError

from ..types import AthenaSettings, CrawlRecord, FilterConfig


logger = logging.getLogger(__name__)


class AthenaQueryError(Exception):
    """Exception raised for Athena query errors."""

    pass


class CrawlQueryBuilder:
    """Query builder for Common Crawl ccindex table with SQL injection protection."""

    def __init__(
        self,
        filter_config: FilterConfig,
        limit: Optional[int] = None,
        crawl: str = "CC-MAIN-2024-33",
    ):
        """Initialize query builder.

        Args:
            filter_config: FilterConfig with search criteria
            limit: Maximum number of results
            crawl: Specific crawl to search (e.g., "CC-MAIN-2025-33")
        """
        self.filter_config = filter_config
        self.limit = limit
        self.crawl = crawl
        self.database = "ccindex"
        self.table = "ccindex"

    @staticmethod
    def _escape_sql_string(value: str) -> str:
        """Escape SQL string to prevent injection attacks.

        Args:
            value: String value to escape

        Returns:
            Escaped string safe for SQL
        """
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value)}")

        dangerous_patterns = [
            r";",  # Statement separators
            r"--",  # SQL comments
            r"/\*",  # Block comments
            r"\*/",  # Block comments
            r"\bUNION\b",  # Union injection
            r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|EXEC|EXECUTE)\b",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"String contains dangerous pattern: {value}")

        escaped = value.replace("'", "''")

        if not re.match(r"^[a-zA-Z0-9._\-/%\s:,']*$", escaped):
            raise ValueError(f"String contains invalid characters: {value}")

        return escaped

    @staticmethod
    def _validate_crawl_id(crawl_id: str) -> str:
        """Validate and sanitize crawl ID.

        Args:
            crawl_id: Crawl identifier to validate

        Returns:
            Validated crawl ID

        Raises:
            ValueError: If crawl ID is invalid
        """
        if not isinstance(crawl_id, str):
            raise ValueError("Crawl ID must be a string")

        if not re.match(r"^CC-MAIN-\d{4}-\d{2}$", crawl_id):
            raise ValueError(f"Invalid crawl ID format: {crawl_id}")

        return crawl_id

    @staticmethod
    def _validate_integer(value: int, min_val: int = 0, max_val: int = 1000000) -> int:
        """Validate integer values.

        Args:
            value: Integer to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Validated integer

        Raises:
            ValueError: If integer is out of range
        """
        if not isinstance(value, int):
            raise ValueError(f"Expected integer, got {type(value)}")

        if not min_val <= value <= max_val:
            raise ValueError(f"Integer {value} not in range [{min_val}, {max_val}]")

        return value

    def to_sql(self, count_only: bool = False) -> str:
        """Build and return SQL query string with SQL injection protection.

        Args:
            count_only: If True, returns SELECT COUNT(*) query instead of full column list

        Returns:
            Complete SQL query for ccindex table

        Raises:
            ValueError: If any input values are invalid or potentially malicious
        """
        safe_crawl = self._validate_crawl_id(self.crawl)

        if count_only:
            select_clause = "SELECT COUNT(*)"
        else:
            select_clause = """
            SELECT 
                url,
                url_host_name,
                fetch_time,
                fetch_status,
                content_mime_type,
                content_charset,
                content_languages,
                warc_filename,
                warc_record_offset,
                warc_record_length
            """

        where_conditions = [f"crawl = '{safe_crawl}'", "subset = 'warc'"]

        if self.filter_config.url_patterns:
            url_conditions = []
            for pattern in self.filter_config.url_patterns:
                sql_pattern = pattern.replace("*", "%")
                safe_pattern = self._escape_sql_string(sql_pattern)
                url_conditions.append(f"url LIKE '{safe_pattern}'")

            if len(url_conditions) == 1:
                where_conditions.append(url_conditions[0])
            else:
                where_conditions.append(f"({' OR '.join(url_conditions)})")

        if self.filter_config.status_codes:
            validated_codes = [
                self._validate_integer(code, 100, 599)
                for code in self.filter_config.status_codes
            ]

            if len(validated_codes) == 1:
                where_conditions.append(f"fetch_status = {validated_codes[0]}")
            else:
                status_list = ",".join(map(str, validated_codes))
                where_conditions.append(f"fetch_status IN ({status_list})")

        if self.filter_config.mime_types:
            mime_conditions = []
            for mime_type in self.filter_config.mime_types:
                safe_mime = self._escape_sql_string(mime_type)
                mime_conditions.append(f"content_mime_type LIKE '{safe_mime}%'")

            if len(mime_conditions) == 1:
                where_conditions.append(mime_conditions[0])
            else:
                where_conditions.append(f"({' OR '.join(mime_conditions)})")

        if self.filter_config.languages:
            lang_conditions = []
            for language in self.filter_config.languages:
                safe_lang = self._escape_sql_string(language)
                lang_conditions.append(f"content_languages LIKE '%{safe_lang}%'")

            if len(lang_conditions) == 1:
                where_conditions.append(lang_conditions[0])
            else:
                where_conditions.append(f"({' OR '.join(lang_conditions)})")

        if self.filter_config.date_from:
            safe_date_from = self._escape_sql_string(self.filter_config.date_from)
            where_conditions.append(f"fetch_time >= '{safe_date_from}'")

        if self.filter_config.date_to:
            safe_date_to = self._escape_sql_string(self.filter_config.date_to)
            where_conditions.append(f"fetch_time <= '{safe_date_to}'")

        if self.filter_config.custom_filters:
            for custom_filter in self.filter_config.custom_filters:
                safe_custom = self._validate_custom_filter(custom_filter)
                where_conditions.append(f"({safe_custom})")

        query = f"""
        {select_clause}
        FROM {self.database}.{self.table}
        WHERE {" AND ".join(where_conditions)}
        """

        if self.limit and not count_only:
            safe_limit = self._validate_integer(self.limit, 1, 100000)
            query += f" LIMIT {safe_limit}"

        return query.strip()

    def _validate_custom_filter(self, custom_filter: str) -> str:
        """Validate custom filter to prevent SQL injection.

        Args:
            custom_filter: Custom SQL WHERE condition

        Returns:
            Validated custom filter

        Raises:
            ValueError: If custom filter contains dangerous patterns
        """
        if not isinstance(custom_filter, str):
            raise ValueError("Custom filter must be a string")

        dangerous_patterns = [
            r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|EXEC|EXECUTE)\b",
            r";",  # Statement separators
            r"--",  # SQL comments
            r"/\*",  # Block comments
            r"\*/",  # Block comments
            r"xp_",  # Extended stored procedures
            r"sp_",  # System stored procedures
            r"UNION\s+SELECT",  # Union injection
            r"@@",  # System variables
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, custom_filter, re.IGNORECASE):
                raise ValueError(
                    f"Custom filter contains dangerous pattern: {custom_filter}"
                )

        if not re.match(
            r'^[a-zA-Z_][a-zA-Z0-9_]*\s*(=|!=|<|>|<=|>=|LIKE|IN)\s*[\'"]?[a-zA-Z0-9._\-/%\s,()]+[\'"]?$',
            custom_filter.strip(),
        ):
            raise ValueError(f"Custom filter format is invalid: {custom_filter}")

        return custom_filter.strip()


class CCAthenaClient:
    """Simple AWS Athena client for querying Common Crawl data.

    Takes AthenaSettings from config.py and creates a boto3 athena client.
    """

    def __init__(self, settings: AthenaSettings):
        """Initialize Athena client with settings.

        Args:
            settings: AthenaSettings instance from config.py

        Raises:
            ValueError: If settings are invalid
            NoCredentialsError: If AWS credentials are not configured
            AthenaQueryError: If Athena setup fails
        """
        if not settings.is_configured():
            raise ValueError(
                "AthenaSettings not properly configured - output_bucket is required"
            )

        self.settings = settings

        try:
            self.athena_client = boto3.client(
                "athena", region_name=settings.region_name
            )
            self.s3_client = boto3.client("s3", region_name=settings.region_name)

            self.athena_client.list_work_groups()

            logger.info(f"CCAthenaClient initialized for region {settings.region_name}")

        except NoCredentialsError:
            raise NoCredentialsError(
                "AWS credentials not found. Please configure AWS credentials using "
                "AWS CLI, environment variables, or IAM roles."
            )
        except (BotoCoreError, Exception) as e:
            raise AthenaQueryError(f"Failed to initialize Athena client: {e}")

    def search(
        self,
        url_pattern: str,
        limit: Optional[int] = None,
        crawl: str = "CC-MAIN-2024-33",
    ) -> List[CrawlRecord]:
        """Search Common Crawl data using Athena.

        Args:
            url_pattern: URL pattern to search (supports SQL LIKE patterns with %)
            limit: Maximum number of results (uses settings.max_results if None)
            crawl: Specific crawl to search (e.g., "CC-MAIN-2024-33")

        Returns:
            List of CrawlRecord objects

        Raises:
            AthenaQueryError: If query fails
        """
        filter_config = FilterConfig(url_patterns=[url_pattern])
        return self.search_with_filter(filter_config, limit, crawl)

    def search_with_filter(
        self,
        filter_config: FilterConfig,
        limit: Optional[int] = None,
        crawl: str = "CC-MAIN-2024-33",
    ) -> List[CrawlRecord]:
        """Search Common Crawl data using FilterConfig.

        Args:
            filter_config: FilterConfig with search criteria
            limit: Maximum number of results (uses settings.max_results if None)
            crawl: Specific crawl to search (e.g., "CC-MAIN-2024-33")

        Returns:
            List of CrawlRecord objects

        Raises:
            AthenaQueryError: If query fails
        """
        if limit is None:
            limit = self.settings.max_results

        query_builder = CrawlQueryBuilder(filter_config, limit, crawl)
        query = query_builder.to_sql()

        logger.info(f"Searching Common Crawl with filter: {filter_config.url_patterns}")
        logger.debug(f"Athena query: {query}")

        try:
            query_execution_id = self._execute_query(query)
            results = self._get_query_results(query_execution_id)

            records = []
            for row in results:
                record = self._row_to_crawl_record(row)
                if record:
                    records.append(record)

            logger.info(f"Retrieved {len(records)} records from Athena")
            return records

        except Exception as e:
            raise AthenaQueryError(f"Athena search failed: {e}")

    def _execute_query(self, query: str) -> str:
        """Execute Athena query and return execution ID."""
        logger.info(f"Executing Athena query: {query}")
        response = self.athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": "ccindex"},
            ResultConfiguration={"OutputLocation": self.settings.output_location},
            WorkGroup="primary",
        )

        query_execution_id = response["QueryExecutionId"]
        self._wait_for_completion(query_execution_id)
        return query_execution_id

    def _wait_for_completion(self, query_execution_id: str) -> None:
        """Wait for Athena query to complete."""
        import time

        start_time = time.time()

        while True:
            response = self.athena_client.get_query_execution(
                QueryExecutionId=query_execution_id
            )

            status = response["QueryExecution"]["Status"]["State"]

            if status == "SUCCEEDED":
                logger.info(f"{query_execution_id} Query completed successfully")
                return
            elif status in ["FAILED", "CANCELLED"]:
                reason = response["QueryExecution"]["Status"].get(
                    "StateChangeReason", "Unknown error"
                )
                logger.warning(f"{query_execution_id} Query failed: {reason}")
                raise AthenaQueryError(f"Query failed: {reason}")
            elif status in ["QUEUED", "RUNNING"]:
                elapsed = time.time() - start_time
                if elapsed > self.settings.timeout_seconds:
                    self.athena_client.stop_query_execution(
                        QueryExecutionId=query_execution_id
                    )
                    logger.warning(
                        f"{query_execution_id} Query timed out after {self.settings.timeout_seconds} seconds"
                    )
                    raise AthenaQueryError(
                        f"Query timed out after {self.settings.timeout_seconds} seconds"
                    )

                time.sleep(2)  # Wait before checking again
            else:
                logger.warning(f"{query_execution_id} Unknown query status: {status}")
                raise AthenaQueryError(f"Unknown query status: {status}")

    def _get_query_results(self, query_execution_id: str) -> List[List[str]]:
        """Get results from completed Athena query."""
        results = []
        paginator = self.athena_client.get_paginator("get_query_results")

        for page in paginator.paginate(
            QueryExecutionId=query_execution_id,
            PaginationConfig={"MaxItems": self.settings.max_results},
        ):
            for i, row in enumerate(page["ResultSet"]["Rows"]):
                if i == 0:
                    continue

                row_data = []
                for data in row["Data"]:
                    value = data.get("VarCharValue", "")
                    row_data.append(value)

                results.append(row_data)

        return results

    def _row_to_crawl_record(self, row: List[str]) -> Optional[CrawlRecord]:
        """Convert Athena result row to CrawlRecord."""
        try:
            if len(row) < 10:
                return None

            url = row[0]
            fetch_time = row[2] if row[2] else ""
            fetch_status = int(row[3]) if row[3] and row[3].isdigit() else 0
            mime_type = row[4] if row[4] else ""
            charset = row[5] if row[5] else ""
            languages_str = row[6] if row[6] else ""
            filename = row[7] if row[7] else ""
            offset = int(row[8]) if row[8] and row[8].isdigit() else 0
            length = int(row[9]) if row[9] and row[9].isdigit() else 0

            languages = []
            if languages_str:
                languages = [lang.strip() for lang in languages_str.split(",")]

            timestamp = ""
            if fetch_time and " " in fetch_time:
                timestamp = fetch_time.split(" ")[0].replace("-", "")

            return CrawlRecord(
                urlkey=url.replace("https://", "").replace("http://", ""),
                timestamp=timestamp,
                url=url,
                mime=mime_type,
                status=fetch_status,
                digest="",  # Not available from Athena
                length=length,
                offset=offset,
                filename=filename,
                charset=charset,
                languages=languages,
            )

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to convert row to CrawlRecord: {e}")
            return None
