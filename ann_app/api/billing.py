from ann_app.utils.api_code import ApiCode
from ann_app.utils.api_response import gen_api_response
from ann_app.services.billing_service import BeamProcessor
from ann_app.utils.db_session import session_scope

from . import api 


@api.route("/count_billing", methods = ["POST"])
def count_billing():
    """
    Handle billing data.
    ---
    responses:
        200:
            description: handle billing data
    """
    beam = BeamProcessor()
    beam.handle_csv_billing_data()
    return gen_api_response(ApiCode.SUCCESS, 'process billing data successfully')


@api.route("/streaming_count_billing", methods = ["GET"])
def streaming_count_billing():
    """
    Handle streaming data from pub/sub
    ---
    responses:
        200:
            description: handle streaming data from pub/sub
    """
    with session_scope() as session:
        beam = BeamProcessor()
        beam.handle_pubsub_billing_data(session = session)
    return gen_api_response(ApiCode.SUCCESS, 'process streaming billing data successfully')
