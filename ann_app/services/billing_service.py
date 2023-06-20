from ann_app.utils.db_session import session_scope
from ann_app.models.billing import BillingReport

from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.transforms.window import FixedWindows
from apache_beam.transforms.trigger import AfterProcessingTime, AccumulationMode
import apache_beam as beam
import csv 

"""
    1. Transforms:
        - Transforms are the operations in your pipeline, and provide a generic processing framework.
        - Apply Transforms:
            [Final Output PCollection] = [Initial Input PCollection] | ([First Transform])
                                                                     | ([Second Transform])
                                                                     | ([Third Transform])
        - Core Beam Transfroms:
            (1) ParDo:
                ParDo is a Beam trnasform for generic parallel processing. 
                The ParDo processing paradigm is similar to the "Map" phase of a Map/Shuffle/Reduce-style algorithm
    
    2. Window
        - Window subdivides a "PCollection" into windows according to the timestamps of its individual elements. 
        - Windows enable grouping operations over unbounded collections by dividing the collection into windows of finite collections 
    3. Watermark 
        - is a guess as to when all data in a certain window is expected to have arrived in the pipeline
        - Data sources are responsible for producing a watermark, and every PCollection must have a watermark that estimates how complete the PCollection is.
        - A windowing function tells the runner how to assign elements to one or more initial windows, and how to merge windows of grouped elements. Each element in a PCollection can only be in one window
"""

# Define column in schema
class Bill(object):
    def __init__(self, service, cost, company):
        self.service = service 
        self.cost = float(cost)
        self.company = company

# Parse csv file for apache beam
class ParseCSV(beam.DoFn):
    def process(self, element):
        reader = csv.reader([element])
        row = next(reader)
        service, cost, company = row[:3]
        return [Bill(service, cost, company)]

# Parse pub/sub data from gcp for apache beam
class ParsePubSub(beam.DoFn):
    def process(self, element):
        data = element.decode('utf-8').split(', ')
        service = data[data.index('service') + 1]
        cost = data[data.index('cost') + 1]
        company = data[data.index('company') + 1]
        return [Bill(service, cost, company)]

# Save data to database
class SaveToDatabase(beam.DoFn):
    def __init__(self, session):
        self.session = session
        
    def process(self, data):
        company, cost = data
        billing_report = BillingReport(
            company = company,
            cost = cost,
            dealing_fee = 0.0
        )
        self.session.add(billing_report)

# Beam Processor class
class BeamProcessor:

    def save_billing_data_to_db(self, data, session=None):
        with session_scope() as session:
            company, cost = data
            billing_report = BillingReport(
                company = company,
                cost = cost,
                dealing_fee = 0.0
            )
            session.add(billing_report)

    def transform_and_save_data(self, billing_data):
        # Composite Transformation -> Group the services by company and sum the total cost
        total_cost_per_company = (
            billing_data 
            | 'Group by Company' >> beam.Map(lambda billing: (billing.company, billing.cost))
            | 'Combine' >> beam.CombinePerKey(sum)
        )

        # Print the total cost per company
        total_cost_per_company | "Print Result" >> beam.Map(print)

        # Save the billing data to the database
        total_cost_per_company | "Save to DB" >> beam.Map(self.save_billing_data_to_db)

    # handle billing data
    def handle_csv_billing_data(self):
        with beam.Pipeline() as pipeline:
            # Specify the CSV file path
            file_path = '/Users/apple/Code/Ann/master/ann_app/services/billing_report.csv'
            
            # Read data from the CSV file 
            lines = pipeline | beam.io.ReadFromText(file_path, skip_header_lines=1)

            # Apply the ParseCSV ParDo function to parse the CSV data
            billing_data = lines | beam.ParDo(ParseCSV())

            # Map/Reduce data, and save data
            self.transform_and_save_data(billing_data)
            

    # handle pub/sub data
    def handle_pubsub_billing_data(self, session=None):
        pipeline_options = PipelineOptions(streaming=True)

        with beam.Pipeline(options=pipeline_options) as pipeline:
            pubsub_data = pipeline | beam.io.ReadFromPubSub(topic='projects/ikala-cloud-swe-dev-sandbox/topics/my-topic')
            # Print data 
            pubsub_data | beam.Map(print)

            parsed_data = (
                # Apply the ParsePubSub ParDo function to parse the Pub/Sub data 
                pubsub_data 
                | "Parse Pub/Sub" >> beam.ParDo(ParsePubSub())
                # Apply a fixed time-based windowing strategy of 1 s
                | "Windowing" >> beam.WindowInto(FixedWindows(1*5))
                | 'Group by Company' >> beam.Map(lambda billing: (billing.company, billing.cost))
                | 'Combine' >> beam.CombinePerKey(sum)
                | "Print Result" >> beam.Map(print)
                | "Save to DB" >> beam.ParDo(SaveToDatabase(session=session))
            )
            
            
            # self.transform_and_save_data(parsed_data)






