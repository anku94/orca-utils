from pptx.oxml.ns import qn
from lxml import etree


def add_appear_animation(slide, shape_ids: list[int]):
    """Add appear-on-click animation for shapes."""
    nsmap = {
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    }

    timing = etree.Element(qn('p:timing'), nsmap=nsmap)
    tn_lst = etree.SubElement(timing, qn('p:tnLst'))

    par = etree.SubElement(tn_lst, qn('p:par'))
    cTn_main = etree.SubElement(par, qn('p:cTn'), id="1", dur="indefinite", restart="never", nodeType="tmRoot")
    child_tn_lst = etree.SubElement(cTn_main, qn('p:childTnLst'))

    seq = etree.SubElement(child_tn_lst, qn('p:seq'), concurrent="1", nextAc="seek")
    cTn_seq = etree.SubElement(seq, qn('p:cTn'), id="2", dur="indefinite", nodeType="mainSeq")
    seq_child_lst = etree.SubElement(cTn_seq, qn('p:childTnLst'))

    node_id = 3
    for i, shape_id in enumerate(shape_ids):
        par_anim = etree.SubElement(seq_child_lst, qn('p:par'))
        cTn_par = etree.SubElement(par_anim, qn('p:cTn'), id=str(node_id), fill="hold")
        node_id += 1

        stCondLst = etree.SubElement(cTn_par, qn('p:stCondLst'))
        if i == 0:
            etree.SubElement(stCondLst, qn('p:cond'), delay="indefinite")
        else:
            etree.SubElement(stCondLst, qn('p:cond'), delay="0")

        child_lst = etree.SubElement(cTn_par, qn('p:childTnLst'))

        par_inner = etree.SubElement(child_lst, qn('p:par'))
        cTn_inner = etree.SubElement(par_inner, qn('p:cTn'), id=str(node_id), fill="hold")
        node_id += 1

        stCondLst2 = etree.SubElement(cTn_inner, qn('p:stCondLst'))
        etree.SubElement(stCondLst2, qn('p:cond'), delay="0")

        child_lst2 = etree.SubElement(cTn_inner, qn('p:childTnLst'))

        par_effect = etree.SubElement(child_lst2, qn('p:par'))
        cTn_effect = etree.SubElement(par_effect, qn('p:cTn'), id=str(node_id), presetID="1", presetClass="entr",
                                       presetSubtype="0", fill="hold", nodeType="clickEffect")
        node_id += 1

        stCondLst3 = etree.SubElement(cTn_effect, qn('p:stCondLst'))
        etree.SubElement(stCondLst3, qn('p:cond'), delay="0")

        child_lst3 = etree.SubElement(cTn_effect, qn('p:childTnLst'))

        set_elem = etree.SubElement(child_lst3, qn('p:set'))
        cBhvr = etree.SubElement(set_elem, qn('p:cBhvr'))
        cTn_bhvr = etree.SubElement(cBhvr, qn('p:cTn'), id=str(node_id), dur="1", fill="hold")
        node_id += 1

        etree.SubElement(cTn_bhvr, qn('p:stCondLst')).append(etree.Element(qn('p:cond'), delay="0"))

        tgtEl = etree.SubElement(cBhvr, qn('p:tgtEl'))
        etree.SubElement(tgtEl, qn('p:spTgt'), spid=str(shape_id))

        attrNameLst = etree.SubElement(cBhvr, qn('p:attrNameLst'))
        etree.SubElement(attrNameLst, qn('p:attrName')).text = "style.visibility"

        to_elem = etree.SubElement(set_elem, qn('p:to'))
        etree.SubElement(to_elem, qn('p:strVal'), val="visible")

    prevCondLst = etree.SubElement(seq, qn('p:prevCondLst'))
    cond_prev = etree.SubElement(prevCondLst, qn('p:cond'), evt="onPrev", delay="0")
    tgtEl_prev = etree.SubElement(cond_prev, qn('p:tgtEl'))
    etree.SubElement(tgtEl_prev, qn('p:sldTgt'))

    nextCondLst = etree.SubElement(seq, qn('p:nextCondLst'))
    cond_next = etree.SubElement(nextCondLst, qn('p:cond'), evt="onNext", delay="0")
    tgtEl_next = etree.SubElement(cond_next, qn('p:tgtEl'))
    etree.SubElement(tgtEl_next, qn('p:sldTgt'))

    slide._element.append(timing)
