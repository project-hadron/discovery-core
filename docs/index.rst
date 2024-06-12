Project Hadron
==============

**Project Hadron** Foundation package is an open-source application framework, written in
pure Python using PyArrow as its canonical and depends on Python and PyArrow packages
only. It provides a set of abstractions that allow a quick to market solution of
component services (microservices) relevant to a use case. Component services are built
for tasks called :ref:``capabilities<Capability Fundamentals>` with each capability
performing a single function. Because they are independently run, each capability can be
updated, deployed, and scaled to meet demand for specific functions of an application.

The foundation package provides the building blocks for a quick to market component
solution providing clear boundaries between concepts. It provides all the core elements
needed to bring a product to market.

.. image:: /source/_images/custom/abstract_classes.png
   :align: center
   :width: 700

For a more in-depth view of **Project Hadron** read the section on :ref:`Building a Capability`
once you have :ref:`installed<Installation>` the package.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   source/installation/installing
   source/custom/index
   source/connectors/basics
   source/others/contribute
