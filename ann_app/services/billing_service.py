from ann_app.utils.db_session import session_scope, get_db 
from ann_app.db_models.billing import BillingReport, PubSubReport
from ann_app.models.billing import BillingReportModel
from ann_app.utils.errors import CustomException
from ann_app.__init__ import create_app 

from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.transforms.window import FixedWindows
from apache_beam.transforms.trigger import AfterWatermark, AfterAny, AccumulationMode, AfterProcessingTime
from apache_beam.io import WriteToText
from http import HTTPStatus
import apache_beam as beam
import csv 
import argparse
import re

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

# Beam Processor class
class BeamProcessor:

    # handle billing data
    def handle_csv_billing_data(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--output',
            dest='output',
            # CHANGE 1/6: (OPTIONAL) The Google Cloud Storage path is required
            # for outputting the results.
            default='/Users/apple/Code/Ann/master/ann_app/services/output.csv',
            help='Output file to write results to.'
        )

        with beam.Pipeline() as pipeline:
            # Specify the CSV file path
            file_path = '/Users/apple/Code/Ann/master/ann_app/services/billing_report.csv'
            
            # Read data from the CSV file 
            lines = pipeline | beam.io.ReadFromText(file_path, skip_header_lines=1)

            # Apply the ParseCSV ParDo function to parse the CSV data
            billing_data = lines | beam.ParDo(ParseCSV())

            # Map/Reduce data, and save data
            self.transform_and_save_data(billing_data)

    def transform_and_save_data(self, billing_data) -> None:
        # Composite Transformation -> Group the services by company and sum the total cost
        (
            billing_data 
            # Map Phase `Map(k1, k2) → list(k2,v2)`
            | 'Group by Company' >> beam.Map(lambda billing: (billing.company, billing.cost))
            # | 'Map Phase result' >> beam.ParDo(print) # This is not worked, as it is a whole ParDo, and afterward Map is not worked 
            # Reduce Phase `Reduce(k2, list(v2)) → list((k3, v3))`
            | 'Combine' >> beam.CombinePerKey(sum)
            # If your ParDo performs a one-to-one mapping of input elements to output elements–that is, 
            # for each input element, it applies a function that produces exactly one output element, 
            # you can use the higher-level Map transform.
            | 'Count Several Fees and Save to DB' >> beam.Map(self.count_fee_and_save_to_db)
        )

    def count_fee_and_save_to_db(self, element) -> None:
        company, total_cost = element 
        tech_fee = total_cost * 0.05 # Applying 5% Serving Fee
        discounted_cost = total_cost * 0.98 # Appying 98% Discount
        print(company, total_cost, discounted_cost, tech_fee) 
        data = BillingReportModel(
            company=company,
            total_cost=total_cost,
            discounted_cost=discounted_cost,
            tech_fee=tech_fee,
        )
        self.save_billing_data_to_db(data)
    
    def save_billing_data_to_db(self, data: BillingReportModel) -> None:
        app = create_app()
        with app.app_context():
            try:
                db = next(get_db())
                print(BillingReport(**data.dict()))
                billing_report = BillingReport(**data.dict())
                db.add(billing_report)
                db.commit()
            except Exception as e:
                db.rollback()
                raise CustomException(code=HTTPStatus.BAD_REQUEST, error_code=400, error_msg=f'create billing data error {str(e)}')
    
    def element_to_tuple(self, element):
        with session_scope() as session:
            billing_report = PubSubReport(
                company = element[0],
                cost = element[1],
                service = 'Cloud Run'
            )
            session.add(billing_report)
        

    # handle pub/sub data
    def handle_pubsub_billing_data(self, session=None):
        pipeline_options = PipelineOptions(streaming=True)
        
        with beam.Pipeline(options=pipeline_options) as pipeline:
            pubsub_data = pipeline | beam.io.ReadFromPubSub(topic='projects/ikala-cloud-swe-dev-sandbox/topics/my-topic')

            # Apply the ParsePubSub ParDo function to parse the Pub/Sub data     
            parsed_data = pubsub_data | "Parse Pub/Sub" >> beam.ParDo(ParsePubSub())
                # Apply a fixed time-based windowing strategy of 1 s
            window_data = parsed_data | "Windowing" >> beam.WindowInto(
                FixedWindows(1*5) , 
                trigger=AfterAny(AfterWatermark( # A watermark is a guess as to when all data in a certain window is expected to have arrived. This is needed because data isn’t always guaranteed to arrive in a pipeline in time order, or to always arrive at predictable intervals.
                    early=AfterProcessingTime(10),
                    late=AfterProcessingTime(30)
                )),
                accumulation_mode=AccumulationMode.DISCARDING
            )
            grouped_data = window_data | 'Group by Company' >> beam.Map(lambda billing: (billing.company, billing.cost))
            combined_data = grouped_data | 'Combine' >> beam.CombinePerKey(sum)
            combined_data | "Print Result" >> beam.Map(print)
            combined_data | "Turn element to tuple" >> beam.Map(self.element_to_tuple)

# handle word count
def handle_word_count(argv=None, save_main_session=True):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        dest='input',
        default='/Users/apple/Code/Ann/master/static/sample.txt', # gs://test_kd/sample.txt
        help='Input file to process.'
    )
    parser.add_argument(
        '--output',
        dest='output',
        # CHANGE 1/6: (OPTIONAL) The Google Cloud Storage path is required
        # for outputting the results.
        default='/Users/apple/Code/Ann/master/static/output.txt', # gs://test_kd/output.txt
        help='Output file to write results to.'
    )
    known_args, pipeline_args = parser.parse_known_args(argv)
    pipeline_options = PipelineOptions(pipeline_args)
    with beam.Pipeline(options=pipeline_options) as p:
        
        # Read the text file[pattern] into a PCollection.
        lines = p | beam.io.ReadFromText(known_args.input)

        # Count the occurrences of each word.
        counts = (
            lines
            | 'Split' >> (
                beam.FlatMap(
                    lambda x: re.findall(r'[A-Za-z\']+', x)
                ).with_output_types(str)
            )
            | 'PairWithOne' >> beam.Map(lambda x: (x, 1))
            | 'GroupAndSum' >> beam.CombinePerKey(sum)
        )
        # Format the counts into a PCollection of strings
        def format_result(word_count):
            (word, count) = word_count
            return '%s: %s' % (word, count)

        output = counts | 'Format' >> beam.Map(format_result)

        # Write the output using a "Write" transform taht has side effects.
        output | WriteToText(known_args.output)




def main():
    # handle_word_count()
    beam = BeamProcessor()
    beam.handle_csv_billing_data()

if __name__ == '__main__':
    main()






