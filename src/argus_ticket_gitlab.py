"Allow argus-server to create tickets in Gitlab"

import logging
from typing import List

import gitlab
from markdownify import markdownify

from argus.incident.ticket.base import TicketPlugin, TicketPluginException

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
        except ValueError as e:
            LOG.exception("Could not import settings for ticket plugin.")
            raise TicketPluginException(f"Gitlab: {e}")

        if "token" not in authentication.keys():
            LOG.error(
                "Gitlab: No token can be found in the authentication information. Please update the setting 'TICKET_AUTHENTICATION_SECRET'."
            )
            raise TicketPluginException(
                "Gitlab: No token can be found in the authentication information. Please update the setting 'TICKET_AUTHENTICATION_SECRET'."
            )

        if "project_namespace_and_name" not in ticket_information.keys():
            LOG.error(
                "Gitlab: No project namespace and name can be found in the ticket information. Please update the setting 'TICKET_INFORMATION'."
            )
            raise TicketPluginException(
                "Gitlab: No project namespace and name can be found in the ticket information. Please update the setting 'TICKET_INFORMATION'."
            )

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
            LOG.exception("Gitlab: Client could not be created.")
            raise TicketPluginException(f"Gitlab: {e}")
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
        except Exception as e:
            LOG.exception("Gitlab: Ticket could not be created.")
            raise TicketPluginException(f"Gitlab: {e}")

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
        except Exception as e:
            LOG.exception("Gitlab: Ticket could not be created.")
            raise TicketPluginException(f"Gitlab: {e}")
        else:
            return ticket.web_url
