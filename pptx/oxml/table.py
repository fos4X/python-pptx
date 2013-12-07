# encoding: utf-8

"""
lxml custom element classes for table-related XML elements.
"""

from __future__ import absolute_import

from lxml import objectify

from pptx.oxml import parse_xml_bytes, XSD_TRUE
from pptx.oxml.core import Element, SubElement
from pptx.oxml.ns import nsdecls, qn


class CT_Table(objectify.ObjectifiedElement):
    """``<a:tbl>`` custom element class"""
    _tbl_tmpl = (
        '<a:tbl %s>\n'
        '  <a:tblPr firstRow="1" bandRow="1">\n'
        '    <a:tableStyleId>%s</a:tableStyleId>\n'
        '  </a:tblPr>\n'
        '  <a:tblGrid/>\n'
        '</a:tbl>' % (nsdecls('a'), '%s')
    )

    BOOLPROPS = (
        'bandCol', 'bandRow', 'firstCol', 'firstRow', 'lastCol', 'lastRow'
    )

    def __getattr__(self, attr):
        """
        Implement getter side of properties. Filters ``__getattr__`` messages
        to ObjectifiedElement base class to intercept messages intended for
        custom property getters.
        """
        if attr in CT_Table.BOOLPROPS:
            return self._get_boolean_property(attr)
        else:
            return super(CT_Table, self).__getattr__(attr)

    def __setattr__(self, attr, value):
        """
        Implement setter side of properties. Filters ``__setattr__`` messages
        to ObjectifiedElement base class to intercept messages intended for
        custom property setters.
        """
        if attr in CT_Table.BOOLPROPS:
            self._set_boolean_property(attr, value)
        else:
            super(CT_Table, self).__setattr__(attr, value)

    def _get_boolean_property(self, propname):
        """
        Generalized getter for the boolean properties on the ``<a:tblPr>``
        child element. Defaults to False if *propname* attribute is missing
        or ``<a:tblPr>`` element itself is not present.
        """
        if not self.has_tblPr:
            return False
        return self.tblPr.get(propname) in ('1', 'true')

    def _set_boolean_property(self, propname, value):
        """
        Generalized setter for boolean properties on the ``<a:tblPr>`` child
        element, setting *propname* attribute appropriately based on *value*.
        If *value* is truthy, the attribute is set to "1"; a tblPr child
        element is added if necessary. If *value* is falsey, the *propname*
        attribute is removed if present, allowing its default value of False
        to be its effective value.
        """
        if value:
            tblPr = self._get_or_insert_tblPr()
            tblPr.set(propname, XSD_TRUE)
        elif not self.has_tblPr:
            pass
        elif propname in self.tblPr.attrib:
            del self.tblPr.attrib[propname]

    @property
    def has_tblPr(self):
        """
        True if this ``<a:tbl>`` element has a ``<a:tblPr>`` child element,
        False otherwise.
        """
        try:
            self.tblPr
            return True
        except AttributeError:
            return False

    def _get_or_insert_tblPr(self):
        """Return tblPr child element, inserting a new one if not present"""
        if not self.has_tblPr:
            tblPr = Element('a:tblPr')
            self.insert(0, tblPr)
        return self.tblPr

    @staticmethod
    def new_tbl(rows, cols, width, height, tableStyleId=None):
        """Return a new ``<p:tbl>`` element tree"""
        # working hypothesis is this is the default table style GUID
        if tableStyleId is None:
            tableStyleId = '{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}'

        xml = CT_Table._tbl_tmpl % (tableStyleId)
        tbl = parse_xml_bytes(xml)

        # add specified number of rows and columns
        rowheight = height/rows
        colwidth = width/cols

        for col in range(cols):
            # adjust width of last col to absorb any div error
            if col == cols-1:
                colwidth = width - ((cols-1) * colwidth)
            SubElement(tbl.tblGrid, 'a:gridCol', w=str(colwidth))

        for row in range(rows):
            # adjust height of last row to absorb any div error
            if row == rows-1:
                rowheight = height - ((rows-1) * rowheight)
            tr = SubElement(tbl, 'a:tr', h=str(rowheight))
            for col in range(cols):
                tr.append(CT_TableCell.new_tc())

        objectify.deannotate(tbl, cleanup_namespaces=True)
        return tbl


class CT_TableCell(objectify.ObjectifiedElement):
    """``<a:tc>`` custom element class"""
    _tc_tmpl = (
        '<a:tc %s>\n'
        '  <a:txBody>\n'
        '    <a:bodyPr/>\n'
        '    <a:lstStyle/>\n'
        '    <a:p/>\n'
        '  </a:txBody>\n'
        '  <a:tcPr/>\n'
        '</a:tc>' % nsdecls('a')
    )

    def __setattr__(self, attr, value):
        """
        This hack is needed to make setter side of properties work,
        overrides ``__setattr__`` defined in ObjectifiedElement super class
        just enough to route messages intended for custom property setters.
        """
        if attr == 'anchor':
            self._set_anchor(value)
        elif attr in ('marT', 'marR', 'marB', 'marL'):
            self._set_marX(attr, value)
        else:
            super(CT_TableCell, self).__setattr__(attr, value)

    @property
    def anchor(self):
        """
        String held in ``anchor`` attribute of ``<a:tcPr>`` child element of
        this ``<a:tc>`` element.
        """
        if self.tcPr is None:
            return None
        return self.tcPr.get('anchor')

    def get_or_add_tcPr(self):
        tcPr = self.tcPr
        if tcPr is None:
            tcPr = Element('a:tcPr')
            idx = 1 if self.txBody else 0
            self.insert(idx, tcPr)
        return tcPr

    def get_or_add_txBody(self):
        """
        Return the <a:rPr> child element of this <a:r> element, newly added
        if not already present.
        """
        if self.txBody is None:
            txBody = Element('a:txBody')
            SubElement(txBody, 'a:bodyPr')
            SubElement(txBody, 'a:p')
            self.insert(0, txBody)
        return self.txBody

    @property
    def marT(self):
        """
        Read/write integer top margin value represented in ``marT`` attribute
        of the ``<a:tcPr>`` child element of this ``<a:tc>`` element. If the
        attribute is not present, the default value ``45720`` (0.05 inches)
        is returned for top and bottom; ``91440`` (0.10 inches) is the
        default for left and right. Assigning |None| to any ``marX``
        property clears that attribute from the element, effectively setting
        it to the default value.
        """
        return self._get_marX('marT', 45720)

    @property
    def marR(self):
        """right margin value represented in ``marR`` attribute"""
        return self._get_marX('marR', 91440)

    @property
    def marB(self):
        """bottom margin value represented in ``marB`` attribute"""
        return self._get_marX('marB', 45720)

    @property
    def marL(self):
        """left margin value represented in ``marL`` attribute"""
        return self._get_marX('marL', 91440)

    @staticmethod
    def new_tc():
        """Return a new ``<a:tc>`` element tree"""
        xml = CT_TableCell._tc_tmpl
        tc = parse_xml_bytes(xml)
        objectify.deannotate(tc, cleanup_namespaces=True)
        return tc

    @property
    def tcPr(self):
        return self.find(qn('a:tcPr'))

    @property
    def txBody(self):
        """
        The <a:txBody> child element, or None if not present.
        """
        return self.find(qn('a:txBody'))

    def _clear_anchor(self):
        """
        Remove anchor attribute from ``<a:tcPr>`` if it exists
        """
        if self.tcPr is None:
            return
        if 'anchor' in self.tcPr.attrib:
            del self.tcPr.attrib['anchor']

    def _get_marX(self, attr_name, default):
        """
        generalized method to get margin values
        """
        if self.tcPr is None:
            return default
        return int(self.tcPr.get(attr_name, default))

    def _set_anchor(self, anchor):
        """
        Set value of anchor attribute on ``<a:tcPr>`` child element
        """
        if anchor is None:
            return self._clear_anchor()
        tcPr = self.get_or_add_tcPr()
        tcPr.set('anchor', anchor)

    def _set_marX(self, marX, value):
        """
        Set value of marX attribute on ``<a:tcPr>`` child element. If *marX*
        is |None|, the marX attribute is removed.
        """
        tcPr = self.get_or_add_tcPr()
        if value is None:
            if marX in tcPr.attrib:
                del tcPr.attrib[marX]
        else:
            tcPr.set(marX, str(value))
