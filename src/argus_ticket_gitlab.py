"Allow argus-server to create tickets in Gitlab"

import logging
from typing import List

import gitlab
from markdownify import markdownify
from requests.exceptions import ConnectionError

from argus.incident.ticket.base import (
    TicketClientException,
    TicketCreationException,
    TicketPlugin,
    TicketPluginException,
    TicketSettingsException,
)

LOG = logging.getLogger(__name__)


__version__ = "1.0"
__all__ = [
    "GitlabPlugin",
]


class GitlabPlugin(TicketPlugin):
    @classmethod
    def import_settings(cls):
        try:
            endpoint, authentication, ticket_information = super().import_settings()
        except TicketSettingsException as e:
            LOG.exception(e)
            raise TicketSettingsException(f"Gitlab: {e}")

        if "token" not in authentication.keys():
            authentication_error = "Gitlab: No authentication token can be found in the authentication information. Please check and update the setting 'TICKET_AUTHENTICATION_SECRET'."
            LOG.exception(authentication_error)
            raise TicketSettingsException(authentication_error)

        if "project_namespace_and_name" not in ticket_information.keys():
            project_namespace_and_name_error = "Gitlab: No project namespace and name can be found in the ticket information. Please check and update the setting 'TICKET_INFORMATION'."
            LOG.error(project_namespace_and_name_error)
            raise TicketSettingsException(project_namespace_and_name_error)

        return endpoint, authentication, ticket_information

    @staticmethod
    def convert_tags_to_dict(tag_dict: dict) -> dict:
        incident_tags_list = [entry["tag"].split("=") for entry in tag_dict]
        return {key: value for key, value in incident_tags_list}

    @staticmethod
    def get_labels(ticket_information: dict, serialized_incident: dict) -> tuple[dict, List[str]]:
        incident_tags = GitlabPlugin.convert_tags_to_dict(serialized_incident["tags"])
        labels = ticket_information.get("labels_set", [])
        labels_mapping = ticket_information.get("labels_mapping", [])
        missing_fields = []

        for field in labels_mapping:
            if type(field) is dict:
                # Information can be found in tags
                label = incident_tags.get(field["tag"], None)
                if label:
                    labels.append(label)
                else:
                    missing_fields.append(field["tag"])
            else:
                label = serialized_incident.get(field, None)
                if label:
                    labels.append(label)
                else:
                    missing_fields.append(field)

        return labels, missing_fields

    @staticmethod
    def create_client(endpoint, authentication):
        """Creates and returns a Gitlab client"""
        try:
            client = gitlab.Gitlab(url=endpoint, private_token=authentication["token"])
        except Exception as e:
            client_error = "Gitlab: Client could not be created."
            LOG.exception(client_error)
            raise TicketClientException(client_error)
        else:
            return client

    @classmethod
    def create_ticket(cls, serialized_incident: dict):
        """
        Creates a Gitlab ticket with the incident as template and returns the
        ticket url
        """
        endpoint, authentication, ticket_information = cls.import_settings()

        client = cls.create_client(endpoint, authentication)

        try:
            project = client.projects.get(ticket_information["project_namespace_and_name"])
        except ConnectionError:
            connection_error = "Gitlab: Could not connect to Gitlab."
            LOG.exception(connection_error)
            raise TicketSettingsException(connection_error)
        except gitlab.exceptions.GitlabAuthenticationError:
            authentication_error = "Gitlab: The authentication details are incorrect. Please check and update the setting 'TICKET_AUTHENTICATION_SECRET'."
            LOG.exception(authentication_error)
            raise TicketSettingsException(authentication_error)
        except gitlab.exceptions.GitlabGetError:
            repo_error = "Gitlab: Could not find repository."
            LOG.exception(repo_error)
            raise TicketSettingsException(repo_error)
        except Exception as e:
            error = f"Gitlab: {e}"
            LOG.exception(error)
            raise TicketPluginException(error)

        label_contents, missing_fields = cls.get_labels(
            ticket_information=ticket_information,
            serialized_incident=serialized_incident,
        )
        repo_labels = project.labels.list()
        labels = [label.name for label in repo_labels if label.name in label_contents]

        html_body = cls.create_html_body(
            serialized_incident={
                "missing_fields": missing_fields,
                **serialized_incident,
            }
        )
        markdown_body = markdownify(html=html_body)

        try:
            ticket = project.issues.create(
                {
                    "title": serialized_incident["description"],
                    "description": markdown_body,
                    "labels": labels,
                }
            )
        except ConnectionError:
            connection_error = "Gitlab: Could not connect to Gitlab."
            LOG.exception(connection_error)
            raise TicketSettingsException(connection_error)
        except gitlab.exceptions.GitlabCreateError as e:
            error = eval(e.response_body.decode())["error_description"]
            LOG.exception("Gitlab: Ticket could not be created.")
            raise TicketCreationException(f"Gitlab: {error}")
        except Exception as e:
            LOG.exception("Gitlab: Ticket could not be created.")
            raise TicketPluginException(f"Gitlab: {e}")
        else:
            return ticket.web_url
