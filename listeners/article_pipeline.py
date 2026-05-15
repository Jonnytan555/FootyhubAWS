from listeners.queue.queue_reader import QueueConsumer


class ArticlePipeline:
    """
    Orchestrates a three-step data pipeline:
      Stage 1: reader → transform → queue  (fetch articles, map to queue shape, write as pending)
      Stage 2: reader → enrich   → save    (read pending/failed, tag with Claude, write to articles)
    """
    def __init__(self, reader, enricher, writer) -> None:
        self.reader = reader
        self.enricher = enricher
        self.writer = writer

    def run(self) -> None:
        data   = self.reader.read()
        result = self.enricher.enrich(data)

        succeeded = [r for r in result if not r.get("_tagging_failed")]
        failed    = [r for r in result if r.get("_tagging_failed")]

        self.writer.write(succeeded)

        if isinstance(self.reader, QueueConsumer):
            self.reader.mark_processed(succeeded)
            self.reader.mark_failed(failed)
