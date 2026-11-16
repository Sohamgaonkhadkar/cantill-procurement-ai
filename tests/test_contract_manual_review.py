import io,hashlib
from pypdf import PdfWriter
from test_api import client
from conftest import contract

def test_scanned_pdf_can_be_corrected_and_approved_manually(client):
    writer=PdfWriter(); writer.add_blank_page(width=300,height=400)
    stream=io.BytesIO(); writer.write(stream); raw=stream.getvalue()
    response=client.post('/api/contracts/upload',files={'file':('scan.pdf',raw,'application/pdf')})
    assert response.status_code==200,response.text
    proposal=response.json()
    assert proposal['contract'] is None and proposal['manual_entry_required']
    assert proposal['source_hash']==hashlib.sha256(raw).hexdigest()
    response=client.post('/api/contracts/proposals/'+proposal['id']+'/approve',json={'contract':contract('MANUAL-SYNTHETIC'),'reason':'Buyer manually verified rates and dates against scanned original'})
    assert response.status_code==200,response.text
    assert response.json()['provenance']['signature_verified'] is False
