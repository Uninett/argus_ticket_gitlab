argus_ticket_gitlab
===================

This is a plugin to create tickets in Gitlab from
`Argus <https://github.com/Uninett/argus-server>`_

Settings
--------

* ``TICKET_ENDPOINT``: ``"https://gitlab.com/"`` or link to self-hosted instance, absolute URL
* ``TICKET_AUTHENTICATION_SECRET``: create a `project access token <https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html>`_ or a `personal access token <https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html>`_ with the scope "``api``"

  ::

    {
        "token": token,
    }

* ``TICKET_INFORMATION``:

  To know which project to create the ticket in the Gitlab API needs to know
  the owner and name of it. To figure out the namespace visit the
  `namespace page <https://docs.gitlab.com/ee/user/namespace/>`_ of the Gitlab
  documentation. The name is the name of the Gitlab project.

  ::

    {
       "project_namespace_and_name": project_namespace_and_name,
    }

  For the Github project 
  `Simple Maven Example <https://gitlab.com/gitlab-examples/maven/simple-maven-example>`_
  the dictionary would look like this:

  ::

    {
       "project_namespace_and_name": "gitlab-examples/maven/simple-maven-example",
    }