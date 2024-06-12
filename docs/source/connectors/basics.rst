Introducing Connectors
======================

Project Hadron is designed using Microservices. Microservices are an architectural
patterns that structures an application as a collection of services, which, themselves
are a component or collection of components. These components are known as
:ref:`Capabilities<Introducing Capabilities>` and each capability has their own set of
communication outlets known as handlers.

Concepts
--------

Connector handlers are a pair of abstract classes, to handle data sourcing and data
persistence. Their design principle follow the same concepts of separation of
concerns through object-oriented design, meaning capabilities use handlers to remain
separated from data type and location until initialization. This allows different
handlers for the same capability across different implementations.

The ConnectorContract class is used as a container class to hold information on the
connection type and location and applied at implementation. By changing the
ConnectorContract you can change the handler.

.. image:: /source/_images/connectors/connector_class_uml.png
  :align: center
  :width: 700

* UML connector contract class diagram

A handler can be thought of as a broker between the internal canonical and the
data storage service format. The ConnectorContract are the dynamic instructions on where
and how the data will be located. Each connection type, AWS S3, MongoDB, Postgres, etc.,
are their own broker or handler and the ConnectorContract the dynamic link between
Capability and a dataset.
