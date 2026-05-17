"""S3-compatible snapshot storage backend.

Uses boto3 for S3 operations. boto3 is lazily imported so that this module
can be imported without boto3 installed (it's an optional dependency).
"""

from __future__ import annotations

from driftguard.schema.models import ContractSnapshot
from driftguard.store.backend import SnapshotBackend


class S3Backend(SnapshotBackend):
    """Store snapshots as JSON objects in an S3-compatible bucket."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "driftguard/",
        endpoint_url: str | None = None,
        region: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix
        self.endpoint_url = endpoint_url
        self.region = region
        self._client = None

    def _get_client(self):
        """Lazy-load boto3 S3 client."""
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:
                raise ImportError(
                    "boto3 is required for S3Backend. Install it with: pip install driftguard-contracts[s3]"
                ) from exc
            kwargs: dict = {}
            if self.endpoint_url:
                kwargs["endpoint_url"] = self.endpoint_url
            if self.region:
                kwargs["region_name"] = self.region
            self._client = boto3.client("s3", **kwargs)
        return self._client

    def _object_key(self, name: str) -> str:
        """Build the S3 object key for a snapshot name."""
        safe_name = name.replace("\\", "/")
        return f"{self.prefix}{safe_name}.json"

    def save(self, snapshot: ContractSnapshot) -> str:
        """Upload snapshot JSON to S3."""
        client = self._get_client()
        key = self._object_key(snapshot.name)
        data = snapshot.model_dump_json(indent=2)
        client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data.encode("utf-8"),
            ContentType="application/json",
        )
        return f"s3://{self.bucket}/{key}"

    def load(self, name: str) -> ContractSnapshot:
        """Download and deserialize a snapshot from S3."""
        client = self._get_client()
        key = self._object_key(name)
        try:
            response = client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"].read().decode("utf-8")
            return ContractSnapshot.model_validate_json(body)
        except client.exceptions.NoSuchKey as exc:
            raise FileNotFoundError(f"Snapshot not found: s3://{self.bucket}/{key}") from exc

    def list_snapshots(self) -> list[str]:
        """List all snapshot names in the S3 prefix."""
        client = self._get_client()
        names: list[str] = []
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".json"):
                    # Strip prefix and .json suffix to get name
                    relative = key[len(self.prefix) :]
                    name = relative[: -len(".json")]
                    names.append(name)
        return sorted(names)

    def delete(self, name: str) -> bool:
        """Delete a snapshot from S3. Return True if deleted, False if not found."""
        if not self.exists(name):
            return False
        client = self._get_client()
        key = self._object_key(name)
        client.delete_object(Bucket=self.bucket, Key=key)
        return True

    def exists(self, name: str) -> bool:
        """Check if a snapshot exists in S3 using head_object."""
        client = self._get_client()
        key = self._object_key(name)
        try:
            client.head_object(Bucket=self.bucket, Key=key)
            return True
        except client.exceptions.ClientError:
            return False
