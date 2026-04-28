import os
import glob
from apps.kb_service.pipelines.ingest import IngestPipeline


class BatchPipeline:
    def __init__(self):
        self.pipeline = IngestPipeline()

    async def run_batch(
        self,
        directory_path: str,
        business_id: str,
        file_patterns: list[str] = ["*.pdf", "*.docx", "*.txt"],
    ) -> list[dict]:
        files = []
        for pattern in file_patterns:
            files.extend(glob.glob(os.path.join(directory_path, pattern)))

        results = []
        for file_path in files:
            result = await self.pipeline.run(
                file_path=file_path,
                business_id=business_id,
            )
            results.append({
                "file": os.path.basename(file_path),
                "job_id": result["job_id"],
                "doc_id": result["doc_id"],
            })
        return results