from src.gii_parser import Law, Norm
from src.law_serializer import law_to_dict, law_to_html, norm_id


def _sample_law() -> Law:
    return Law(
        jurabk="BGB",
        amtabk="BGB",
        ausfertigung_datum="1896-08-18",
        langue="Bürgerliches Gesetzbuch",
        norms=[
            Norm(enbez="§ 1", titel="Rechtsfähigkeit", text_xml="<P>Die Rechtsfähigkeit...</P>"),
            Norm(enbez="§ 2", titel=None, text_xml="<P>Volljährig...</P>"),
            Norm(enbez="Art. 3", titel="Titel", text_xml=None),
            Norm(enbez=None, titel=None, text_xml="<P>Ohne enbez</P>"),
        ],
    )


# --- norm_id ---

def test_norm_id_paragraph():
    assert norm_id("§ 1", 0) == "1"

def test_norm_id_paragraph_alpha():
    assert norm_id("§ 1a", 0) == "1a"

def test_norm_id_article():
    assert norm_id("Art. 2", 0) == "art-2"

def test_norm_id_none_uses_index():
    assert norm_id(None, 5) == "norm-5"

def test_norm_id_anlage():
    assert norm_id("Anlage 3", 0) == "anlage-3"


# --- law_to_dict ---

def test_law_to_dict_metadata():
    d = law_to_dict("bgb", _sample_law())
    assert d["slug"] == "bgb"
    assert d["jurabk"] == "BGB"
    assert d["langue"] == "Bürgerliches Gesetzbuch"
    assert d["ausfertigung_datum"] == "1896-08-18"

def test_law_to_dict_norm_count():
    d = law_to_dict("bgb", _sample_law())
    assert d["norm_count"] == 4
    assert len(d["norms"]) == 4

def test_law_to_dict_norm_shape():
    d = law_to_dict("bgb", _sample_law())
    first = d["norms"][0]
    assert first["norm_id"] == "1"
    assert first["enbez"] == "§ 1"
    assert first["titel"] == "Rechtsfähigkeit"
    assert first["text_xml"] == "<P>Die Rechtsfähigkeit...</P>"

def test_law_to_dict_null_fields_preserved():
    d = law_to_dict("bgb", _sample_law())
    assert d["norms"][2]["text_xml"] is None   # Art. 3 has no text
    assert d["norms"][3]["enbez"] is None


# --- law_to_html ---

def test_law_to_html_has_doctype():
    h = law_to_html("bgb", _sample_law())
    assert h.startswith("<!DOCTYPE html>")

def test_law_to_html_has_title():
    h = law_to_html("bgb", _sample_law())
    assert "BGB" in h
    assert "Bürgerliches Gesetzbuch" in h

def test_law_to_html_section_ids():
    h = law_to_html("bgb", _sample_law())
    assert 'id="1"' in h
    assert 'id="art-3"' in h
    assert 'id="norm-3"' in h   # the norm with enbez=None is at index 3

def test_law_to_html_text_embedded():
    h = law_to_html("bgb", _sample_law())
    assert "<P>Die Rechtsfähigkeit...</P>" in h

def test_law_to_html_missing_jurabk():
    law = Law(jurabk=None, amtabk=None, ausfertigung_datum=None, langue=None, norms=[])
    h = law_to_html("testslug", law)
    assert "testslug" in h
