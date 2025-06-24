import uuid

from dashboard_graph.api.models import LogMetadata
from dashboard_graph.api.routers.presentation.models import GenerateTitleRequest
from dashboard_graph.api.services.instances import temp_file_service
from dashboard_graph.api.services.logging import LoggingService
from dashboard_graph.api.sql_models import PresentationSqlModel
from dashboard_graph.ppt_config_generator.models import PresentationTitlesModel
from dashboard_graph.ppt_config_generator.ppt_title_summary_generator import generate_ppt_titles
from dashboard_graph.api.services.database import get_sql_session


class PresentationTitlesGenerateHandler:
    def __init__(self, data: GenerateTitleRequest):
        self.data = data

        self.session = str(uuid.uuid4())
        self.temp_dir = temp_file_service.create_temp_dir(self.session)

    def __del__(self):
        temp_file_service.cleanup_temp_dir(self.temp_dir)

    async def post(self, logging_service: LoggingService, log_metadata: LogMetadata):

        logging_service.logger.info(
            "Called PresentationTitlesGenerateHandler.post",
            extra=log_metadata.model_dump(),
        )
        logging_service.logger.info(
            logging_service.message(self.data.model_dump(mode="json")),
            extra=log_metadata.model_dump(),
        )

        with get_sql_session() as sql_session:
            presentation = sql_session.get(
                PresentationSqlModel, self.data.presentation_id
            )

            presentation_titles: PresentationTitlesModel = await generate_ppt_titles(
                presentation.prompt,
                presentation.n_slides,
                presentation.summary,
                presentation.language,
            )

            presentation.title = presentation_titles.presentation_title
            presentation.titles = presentation_titles.titles

            sql_session.commit()
            sql_session.refresh(presentation)

        logging_service.logger.info(
            logging_service.message(presentation.model_dump(mode="json")),
            extra=log_metadata.model_dump(),
        )

        return presentation
