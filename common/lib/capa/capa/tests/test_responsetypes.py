"""
Tests of responsetypes
"""


from datetime import datetime
import json
from nose.plugins.skip import SkipTest
import os
import unittest
import textwrap

from . import test_system

import capa.capa_problem as lcp
from capa.correctmap import CorrectMap
from capa.util import convert_files_to_filenames
from capa.xqueue_interface import dateformat

class ResponseTest(unittest.TestCase):
    """ Base class for tests of capa responses."""
    
    xml_factory_class = None

    def setUp(self):
        if self.xml_factory_class:
            self.xml_factory = self.xml_factory_class()

    def build_problem(self, **kwargs):
        xml = self.xml_factory.build_xml(**kwargs)
        return lcp.LoncapaProblem(xml, '1', system=test_system)

    def assert_grade(self, problem, submission, expected_correctness):
        input_dict = {'1_2_1': submission}
        correct_map = problem.grade_answers(input_dict)
        self.assertEquals(correct_map.get_correctness('1_2_1'), expected_correctness)

    def assert_multiple_grade(self, problem, correct_answers, incorrect_answers):
        for input_str in correct_answers:
            result = problem.grade_answers({'1_2_1': input_str}).get_correctness('1_2_1')
            self.assertEqual(result, 'correct',
                        msg="%s should be marked correct" % str(input_str))

        for input_str in incorrect_answers:
            result = problem.grade_answers({'1_2_1': input_str}).get_correctness('1_2_1')
            self.assertEqual(result, 'incorrect', 
                            msg="%s should be marked incorrect" % str(input_str))

class MultiChoiceResponseTest(ResponseTest):
    from response_xml_factory import MultipleChoiceResponseXMLFactory
    xml_factory_class = MultipleChoiceResponseXMLFactory

    def test_multiple_choice_grade(self):
        problem = self.build_problem(choices=[False, True, False])

        # Ensure that we get the expected grades
        self.assert_grade(problem, 'choice_0', 'incorrect')
        self.assert_grade(problem, 'choice_1', 'correct')
        self.assert_grade(problem, 'choice_2', 'incorrect')

    def test_named_multiple_choice_grade(self):
        problem = self.build_problem(choices=[False, True, False],
                                    choice_names=["foil_1", "foil_2", "foil_3"])
        
        # Ensure that we get the expected grades
        self.assert_grade(problem, 'choice_foil_1', 'incorrect')
        self.assert_grade(problem, 'choice_foil_2', 'correct')
        self.assert_grade(problem, 'choice_foil_3', 'incorrect')


class TrueFalseResponseTest(ResponseTest):
    from response_xml_factory import TrueFalseResponseXMLFactory
    xml_factory_class = TrueFalseResponseXMLFactory

    def test_true_false_grade(self):
        problem = self.build_problem(choices=[False, True, True])

        # Check the results
        # Mark correct if and only if ALL (and only) correct choices selected
        self.assert_grade(problem, 'choice_0', 'incorrect')
        self.assert_grade(problem, 'choice_1', 'incorrect')
        self.assert_grade(problem, 'choice_2', 'incorrect')
        self.assert_grade(problem, ['choice_0', 'choice_1', 'choice_2'], 'incorrect')
        self.assert_grade(problem, ['choice_0', 'choice_2'], 'incorrect')
        self.assert_grade(problem, ['choice_0', 'choice_1'], 'incorrect')
        self.assert_grade(problem, ['choice_1', 'choice_2'], 'correct')

        # Invalid choices should be marked incorrect (we have no choice 3)
        self.assert_grade(problem, 'choice_3', 'incorrect')
        self.assert_grade(problem, 'not_a_choice', 'incorrect')

    def test_named_true_false_grade(self):
        problem = self.build_problem(choices=[False, True, True],
                                    choice_names=['foil_1','foil_2','foil_3'])

        # Check the results
        # Mark correct if and only if ALL (and only) correct chocies selected
        self.assert_grade(problem, 'choice_foil_1', 'incorrect')
        self.assert_grade(problem, 'choice_foil_2', 'incorrect')
        self.assert_grade(problem, 'choice_foil_3', 'incorrect')
        self.assert_grade(problem, ['choice_foil_1', 'choice_foil_2', 'choice_foil_3'], 'incorrect')
        self.assert_grade(problem, ['choice_foil_1', 'choice_foil_3'], 'incorrect')
        self.assert_grade(problem, ['choice_foil_1', 'choice_foil_2'], 'incorrect')
        self.assert_grade(problem, ['choice_foil_2', 'choice_foil_3'], 'correct')

        # Invalid choices should be marked incorrect
        self.assert_grade(problem, 'choice_foil_4', 'incorrect')
        self.assert_grade(problem, 'not_a_choice', 'incorrect')

class ImageResponseTest(ResponseTest):
    from response_xml_factory import ImageResponseXMLFactory
    xml_factory_class = ImageResponseXMLFactory

    def test_rectangle_grade(self):
        # Define a rectangle with corners (10,10) and (20,20)
        problem = self.build_problem(rectangle="(10,10)-(20,20)")

        # Anything inside the rectangle (and along the borders) is correct
        # Everything else is incorrect
        correct_inputs = ["[12,19]", "[10,10]", "[20,20]", 
                            "[10,15]", "[20,15]", "[15,10]", "[15,20]"]
        incorrect_inputs = ["[4,6]", "[25,15]", "[15,40]", "[15,4]"]
        self.assert_multiple_grade(problem, correct_inputs, incorrect_inputs)

    def test_multiple_rectangles_grade(self):
        # Define two rectangles
        rectangle_str = "(10,10)-(20,20);(100,100)-(200,200)"

        # Expect that only points inside the rectangles are marked correct
        problem = self.build_problem(rectangle=rectangle_str)
        correct_inputs = ["[12,19]", "[120, 130]"]
        incorrect_inputs = ["[4,6]", "[25,15]", "[15,40]", "[15,4]",
                            "[50,55]", "[300, 14]", "[120, 400]"]
        self.assert_multiple_grade(problem, correct_inputs, incorrect_inputs)

    def test_region_grade(self):
        # Define a triangular region with corners (0,0), (5,10), and (0, 10)
        region_str = "[ [1,1], [5,10], [0,10] ]"

        # Expect that only points inside the triangle are marked correct
        problem = self.build_problem(regions=region_str)
        correct_inputs = ["[2,4]", "[1,3]"]
        incorrect_inputs = ["[0,0]", "[3,5]", "[5,15]", "[30, 12]"]
        self.assert_multiple_grade(problem, correct_inputs, incorrect_inputs)

    def test_multiple_regions_grade(self):
        # Define multiple regions that the user can select
        region_str="[[[10,10], [20,10], [20, 30]], [[100,100], [120,100], [120,150]]]"

        # Expect that only points inside the regions are marked correct
        problem = self.build_problem(regions=region_str)
        correct_inputs = ["[15,12]", "[110,112]"]
        incorrect_inputs = ["[0,0]", "[600,300]"]
        self.assert_multiple_grade(problem, correct_inputs, incorrect_inputs)

    def test_region_and_rectangle_grade(self):
        rectangle_str = "(100,100)-(200,200)"
        region_str="[[10,10], [20,10], [20, 30]]"

        # Expect that only points inside the rectangle or region are marked correct
        problem = self.build_problem(regions=region_str, rectangle=rectangle_str)
        correct_inputs = ["[13,12]", "[110,112]"]
        incorrect_inputs = ["[0,0]", "[600,300]"]
        self.assert_multiple_grade(problem, correct_inputs, incorrect_inputs)


class SymbolicResponseTest(unittest.TestCase):
    def test_sr_grade(self):
        raise SkipTest()  # This test fails due to dependencies on a local copy of snuggletex-webapp. Until we have figured that out, we'll just skip this test
        symbolicresponse_file = os.path.dirname(__file__) + "/test_files/symbolicresponse.xml"
        test_lcp = lcp.LoncapaProblem(open(symbolicresponse_file).read(), '1', system=test_system)
        correct_answers = {'1_2_1': 'cos(theta)*[[1,0],[0,1]] + i*sin(theta)*[[0,1],[1,0]]',
                           '1_2_1_dynamath': '''
<math xmlns="http://www.w3.org/1998/Math/MathML">
  <mstyle displaystyle="true">
    <mrow>
      <mi>cos</mi>
      <mrow>
        <mo>(</mo>
        <mi>&#x3B8;</mi>
        <mo>)</mo>
      </mrow>
    </mrow>
    <mo>&#x22C5;</mo>
    <mrow>
      <mo>[</mo>
      <mtable>
        <mtr>
          <mtd>
            <mn>1</mn>
          </mtd>
          <mtd>
            <mn>0</mn>
          </mtd>
        </mtr>
        <mtr>
          <mtd>
            <mn>0</mn>
          </mtd>
          <mtd>
            <mn>1</mn>
          </mtd>
        </mtr>
      </mtable>
      <mo>]</mo>
    </mrow>
    <mo>+</mo>
    <mi>i</mi>
    <mo>&#x22C5;</mo>
    <mrow>
      <mi>sin</mi>
      <mrow>
        <mo>(</mo>
        <mi>&#x3B8;</mi>
        <mo>)</mo>
      </mrow>
    </mrow>
    <mo>&#x22C5;</mo>
    <mrow>
      <mo>[</mo>
      <mtable>
        <mtr>
          <mtd>
            <mn>0</mn>
          </mtd>
          <mtd>
            <mn>1</mn>
          </mtd>
        </mtr>
        <mtr>
          <mtd>
            <mn>1</mn>
          </mtd>
          <mtd>
            <mn>0</mn>
          </mtd>
        </mtr>
      </mtable>
      <mo>]</mo>
    </mrow>
  </mstyle>
</math>
''',
                           }
        wrong_answers = {'1_2_1': '2',
                         '1_2_1_dynamath': '''
                         <math xmlns="http://www.w3.org/1998/Math/MathML">
  <mstyle displaystyle="true">
    <mn>2</mn>
  </mstyle>
</math>''',
                        }
        self.assertEquals(test_lcp.grade_answers(correct_answers).get_correctness('1_2_1'), 'correct')
        self.assertEquals(test_lcp.grade_answers(wrong_answers).get_correctness('1_2_1'), 'incorrect')


class OptionResponseTest(ResponseTest):
    from response_xml_factory import OptionResponseXMLFactory
    xml_factory_class = OptionResponseXMLFactory

    def test_grade(self):
        problem = self.build_problem(options=["first", "second", "third"], 
                                    correct_option="second")

        # Assert that we get the expected grades
        self.assert_grade(problem, "first", "incorrect")
        self.assert_grade(problem, "second", "correct")
        self.assert_grade(problem, "third", "incorrect")

        # Options not in the list should be marked incorrect
        self.assert_grade(problem, "invalid_option", "incorrect")


class FormulaResponseTest(ResponseTest):
    from response_xml_factory import FormulaResponseXMLFactory
    xml_factory_class = FormulaResponseXMLFactory

    def test_grade(self):
        # Sample variables x and y in the range [-10, 10]
        sample_dict = {'x': (-10, 10), 'y': (-10, 10)}

        # The expected solution is numerically equivalent to x+2y
        problem = self.build_problem(sample_dict=sample_dict,
                                    num_samples=10,
                                    tolerance=0.01,
                                    answer="x+2*y")

        # Expect an equivalent formula to be marked correct
        # 2x - x + y + y = x + 2y
        input_formula = "2*x - x + y + y"
        self.assert_grade(problem, input_formula, "correct")

        # Expect an incorrect formula to be marked incorrect
        # x + y != x + 2y
        input_formula = "x + y"
        self.assert_grade(problem, input_formula, "incorrect")

    def test_hint(self):
        # Sample variables x and y in the range [-10, 10]
        sample_dict = {'x': (-10, 10), 'y': (-10,10) }

        # Give a hint if the user leaves off the coefficient
        # or leaves out x
        hints = [('x + 3*y', 'y_coefficient', 'Check the coefficient of y'),
                ('2*y', 'missing_x', 'Try including the variable x')]


        # The expected solution is numerically equivalent to x+2y
        problem = self.build_problem(sample_dict=sample_dict,
                                    num_samples=10,
                                    tolerance=0.01,
                                    answer="x+2*y",
                                    hints=hints)

        # Expect to receive a hint  if we add an extra y
        input_dict = {'1_2_1': "x + 2*y + y"}
        correct_map = problem.grade_answers(input_dict)
        self.assertEquals(correct_map.get_hint('1_2_1'),
                'Check the coefficient of y')

        # Expect to receive a hint if we leave out x
        input_dict = {'1_2_1': "2*y"}
        correct_map = problem.grade_answers(input_dict)
        self.assertEquals(correct_map.get_hint('1_2_1'),
                'Try including the variable x')


    def test_script(self):
        # Calculate the answer using a script
        script = "calculated_ans = 'x+x'"

        # Sample x in the range [-10,10]
        sample_dict = {'x': (-10, 10)}

        # The expected solution is numerically equivalent to 2*x
        problem = self.build_problem(sample_dict=sample_dict,
                                    num_samples=10,
                                    tolerance=0.01,
                                    answer="$calculated_ans",
                                    script=script)

        # Expect that the inputs are graded correctly
        self.assert_grade(problem, '2*x', 'correct')
        self.assert_grade(problem, '3*x', 'incorrect')


class StringResponseTest(ResponseTest):
    from response_xml_factory import StringResponseXMLFactory
    xml_factory_class = StringResponseXMLFactory


    def test_case_sensitive(self):
        problem = self.build_problem(answer="Second", case_sensitive=True)

        # Exact string should be correct
        self.assert_grade(problem, "Second", "correct")

        # Other strings and the lowercase version of the string are incorrect
        self.assert_grade(problem, "Other String", "incorrect")
        self.assert_grade(problem, "second", "incorrect")

    def test_case_insensitive(self):
        problem = self.build_problem(answer="Second", case_sensitive=False)

        # Both versions of the string should be allowed, regardless
        # of capitalization
        self.assert_grade(problem, "Second", "correct")
        self.assert_grade(problem, "second", "correct")

        # Other strings are not allowed
        self.assert_grade(problem, "Other String", "incorrect")

    def test_hints(self):
        hints = [("wisconsin", "wisc", "The state capital of Wisconsin is Madison"),
                ("minnesota", "minn", "The state capital of Minnesota is St. Paul")]

        problem = self.build_problem(answer="Michigan", 
                                    case_sensitive=False, 
                                    hints=hints)

        # We should get a hint for Wisconsin
        input_dict = {'1_2_1': 'Wisconsin'}
        correct_map = problem.grade_answers(input_dict)
        self.assertEquals(correct_map.get_hint('1_2_1'),
                        "The state capital of Wisconsin is Madison")

        # We should get a hint for Minnesota
        input_dict = {'1_2_1': 'Minnesota'}
        correct_map = problem.grade_answers(input_dict)
        self.assertEquals(correct_map.get_hint('1_2_1'),
                        "The state capital of Minnesota is St. Paul")

        # We should NOT get a hint for Michigan (the correct answer)
        input_dict = {'1_2_1': 'Michigan'}
        correct_map = problem.grade_answers(input_dict)
        self.assertEquals(correct_map.get_hint('1_2_1'), "")

        # We should NOT get a hint for any other string
        input_dict = {'1_2_1': 'California'}
        correct_map = problem.grade_answers(input_dict)
        self.assertEquals(correct_map.get_hint('1_2_1'), "")

class CodeResponseTest(ResponseTest):
    from response_xml_factory import CodeResponseXMLFactory
    xml_factory_class = CodeResponseXMLFactory

    def setUp(self):
        super(CodeResponseTest, self).setUp()

        grader_payload = json.dumps({"grader": "ps04/grade_square.py"})
        self.problem = self.build_problem(initial_display="def square(x):",
                                        answer_display="answer",
                                        grader_payload=grader_payload,
                                        num_responses=2)

    @staticmethod
    def make_queuestate(key, time):
        timestr = datetime.strftime(time, dateformat)
        return {'key': key, 'time': timestr}

    def test_is_queued(self):
        """
        Simple test of whether LoncapaProblem knows when it's been queued
        """

        answer_ids = sorted(self.problem.get_question_answers())

        # CodeResponse requires internal CorrectMap state. Build it now in the unqueued state
        cmap = CorrectMap()
        for answer_id in answer_ids:
            cmap.update(CorrectMap(answer_id=answer_id, queuestate=None))
        self.problem.correct_map.update(cmap)

        self.assertEquals(self.problem.is_queued(), False)

        # Now we queue the LCP
        cmap = CorrectMap()
        for i, answer_id in enumerate(answer_ids):
            queuestate = CodeResponseTest.make_queuestate(i, datetime.now())
            cmap.update(CorrectMap(answer_id=answer_ids[i], queuestate=queuestate))
        self.problem.correct_map.update(cmap)

        self.assertEquals(self.problem.is_queued(), True)


    def test_update_score(self):
        '''
        Test whether LoncapaProblem.update_score can deliver queued result to the right subproblem
        '''
        answer_ids = sorted(self.problem.get_question_answers())

        # CodeResponse requires internal CorrectMap state. Build it now in the queued state
        old_cmap = CorrectMap()
        for i, answer_id in enumerate(answer_ids):
            queuekey = 1000 + i
            queuestate = CodeResponseTest.make_queuestate(1000 + i, datetime.now())
            old_cmap.update(CorrectMap(answer_id=answer_ids[i], queuestate=queuestate))

        # Message format common to external graders
        grader_msg = '<span>MESSAGE</span>'   # Must be valid XML
        correct_score_msg = json.dumps({'correct': True, 'score': 1, 'msg': grader_msg})
        incorrect_score_msg = json.dumps({'correct': False, 'score': 0, 'msg': grader_msg})

        xserver_msgs = {'correct': correct_score_msg,
                        'incorrect': incorrect_score_msg, }

        # Incorrect queuekey, state should not be updated
        for correctness in ['correct', 'incorrect']:
            self.problem.correct_map = CorrectMap()
            self.problem.correct_map.update(old_cmap)  # Deep copy

            self.problem.update_score(xserver_msgs[correctness], queuekey=0)
            self.assertEquals(self.problem.correct_map.get_dict(), old_cmap.get_dict())  # Deep comparison

            for answer_id in answer_ids:
                self.assertTrue(self.problem.correct_map.is_queued(answer_id))  # Should be still queued, since message undelivered

        # Correct queuekey, state should be updated
        for correctness in ['correct', 'incorrect']:
            for i, answer_id in enumerate(answer_ids):
                self.problem.correct_map = CorrectMap()
                self.problem.correct_map.update(old_cmap)

                new_cmap = CorrectMap()
                new_cmap.update(old_cmap)
                npoints = 1 if correctness == 'correct' else 0
                new_cmap.set(answer_id=answer_id, npoints=npoints, correctness=correctness, msg=grader_msg, queuestate=None)

                self.problem.update_score(xserver_msgs[correctness], queuekey=1000 + i)
                self.assertEquals(self.problem.correct_map.get_dict(), new_cmap.get_dict())

                for j, test_id in enumerate(answer_ids):
                    if j == i:
                        self.assertFalse(self.problem.correct_map.is_queued(test_id))  # Should be dequeued, message delivered
                    else:
                        self.assertTrue(self.problem.correct_map.is_queued(test_id))  # Should be queued, message undelivered


    def test_recentmost_queuetime(self):
        '''
        Test whether the LoncapaProblem knows about the time of queue requests
        '''
        answer_ids = sorted(self.problem.get_question_answers())

        # CodeResponse requires internal CorrectMap state. Build it now in the unqueued state
        cmap = CorrectMap()
        for answer_id in answer_ids:
            cmap.update(CorrectMap(answer_id=answer_id, queuestate=None))
        self.problem.correct_map.update(cmap)

        self.assertEquals(self.problem.get_recentmost_queuetime(), None)

        # CodeResponse requires internal CorrectMap state. Build it now in the queued state
        cmap = CorrectMap()
        for i, answer_id in enumerate(answer_ids):
            queuekey = 1000 + i
            latest_timestamp = datetime.now()
            queuestate = CodeResponseTest.make_queuestate(1000 + i, latest_timestamp)
            cmap.update(CorrectMap(answer_id=answer_id, queuestate=queuestate))
        self.problem.correct_map.update(cmap)

        # Queue state only tracks up to second
        latest_timestamp = datetime.strptime(datetime.strftime(latest_timestamp, dateformat), dateformat)

        self.assertEquals(self.problem.get_recentmost_queuetime(), latest_timestamp)

    def test_convert_files_to_filenames(self):
        '''
        Test whether file objects are converted to filenames without altering other structures
        '''
        problem_file = os.path.join(os.path.dirname(__file__), "test_files/filename_convert_test.txt")
        with open(problem_file) as fp:
            answers_with_file = {'1_2_1': 'String-based answer',
                                 '1_3_1': ['answer1', 'answer2', 'answer3'],
                                 '1_4_1': [fp, fp]}
            answers_converted = convert_files_to_filenames(answers_with_file)
            self.assertEquals(answers_converted['1_2_1'], 'String-based answer')
            self.assertEquals(answers_converted['1_3_1'], ['answer1', 'answer2', 'answer3'])
            self.assertEquals(answers_converted['1_4_1'], [fp.name, fp.name])

class ChoiceResponseTest(ResponseTest):
    from response_xml_factory import ChoiceResponseXMLFactory
    xml_factory_class = ChoiceResponseXMLFactory

    def test_radio_group_grade(self):
        problem = self.build_problem(choice_type='radio', 
                                        choices=[False, True, False])

        # Check that we get the expected results
        self.assert_grade(problem, 'choice_0', 'incorrect')
        self.assert_grade(problem, 'choice_1', 'correct')
        self.assert_grade(problem, 'choice_2', 'incorrect')

        # No choice 3 exists --> mark incorrect
        self.assert_grade(problem, 'choice_3', 'incorrect')


    def test_checkbox_group_grade(self):
        problem = self.build_problem(choice_type='checkbox',
                                        choices=[False, True, True])

        # Check that we get the expected results
        # (correct if and only if BOTH correct choices chosen)
        self.assert_grade(problem, ['choice_1', 'choice_2'], 'correct')
        self.assert_grade(problem, 'choice_1', 'incorrect')
        self.assert_grade(problem, 'choice_2', 'incorrect')
        self.assert_grade(problem, ['choice_0', 'choice_1'], 'incorrect')
        self.assert_grade(problem, ['choice_0', 'choice_2'], 'incorrect')

        # No choice 3 exists --> mark incorrect
        self.assert_grade(problem, 'choice_3', 'incorrect')


class JavascriptResponseTest(ResponseTest):
    from response_xml_factory import JavascriptResponseXMLFactory
    xml_factory_class = JavascriptResponseXMLFactory

    def test_grade(self):
        # Compile coffee files into javascript used by the response
        coffee_file_path = os.path.dirname(__file__) + "/test_files/js/*.coffee"
        os.system("coffee -c %s" % (coffee_file_path))

        problem = self.build_problem(generator_src="test_problem_generator.js",
                                    grader_src="test_problem_grader.js",
                                    display_class="TestProblemDisplay",
                                    display_src="test_problem_display.js",
                                    param_dict={'value': '4'})

        # Test that we get graded correctly
        self.assert_grade(problem, json.dumps({0:4}), "correct")
        self.assert_grade(problem, json.dumps({0:5}), "incorrect")

class NumericalResponseTest(ResponseTest):
    from response_xml_factory import NumericalResponseXMLFactory
    xml_factory_class = NumericalResponseXMLFactory

    def test_grade_exact(self):
        problem = self.build_problem(question_text="What is 2 + 2?",
                                        explanation="The answer is 4",
                                        answer=4)
        correct_responses = ["4", "4.0", "4.00"]
        incorrect_responses = ["", "3.9", "4.1", "0"]
        self.assert_multiple_grade(problem, correct_responses, incorrect_responses)
        

    def test_grade_decimal_tolerance(self):
        problem = self.build_problem(question_text="What is 2 + 2 approximately?",
                                        explanation="The answer is 4",
                                        answer=4,
                                        tolerance=0.1)
        correct_responses = ["4.0", "4.00", "4.09", "3.91"] 
        incorrect_responses = ["", "4.11", "3.89", "0"]
        self.assert_multiple_grade(problem, correct_responses, incorrect_responses)
                        
    def test_grade_percent_tolerance(self):
        problem = self.build_problem(question_text="What is 2 + 2 approximately?",
                                        explanation="The answer is 4",
                                        answer=4,
                                        tolerance="10%")
        correct_responses = ["4.0", "4.3", "3.7", "4.30", "3.70"]
        incorrect_responses = ["", "4.5", "3.5", "0"]
        self.assert_multiple_grade(problem, correct_responses, incorrect_responses)

    def test_grade_with_script(self):
        script_text = "computed_response = math.sqrt(4)"
        problem = self.build_problem(question_text="What is sqrt(4)?",
                                        explanation="The answer is 2",
                                        answer="$computed_response",
                                        script=script_text)
        correct_responses = ["2", "2.0"]
        incorrect_responses = ["", "2.01", "1.99", "0"]
        self.assert_multiple_grade(problem, correct_responses, incorrect_responses)

    def test_grade_with_script_and_tolerance(self):
        script_text = "computed_response = math.sqrt(4)"
        problem = self.build_problem(question_text="What is sqrt(4)?",
                                        explanation="The answer is 2",
                                        answer="$computed_response",
                                        tolerance="0.1",
                                        script=script_text)
        correct_responses = ["2", "2.0", "2.05", "1.95"]
        incorrect_responses = ["", "2.11", "1.89", "0"]
        self.assert_multiple_grade(problem, correct_responses, incorrect_responses)


class CustomResponseTest(ResponseTest):
    from response_xml_factory import CustomResponseXMLFactory
    xml_factory_class = CustomResponseXMLFactory

    def test_inline_code(self):

        # For inline code, we directly modify global context variables
        # 'answers' is a list of answers provided to us
        # 'correct' is a list we fill in with True/False
        # 'expect' is given to us (if provided in the XML)
        inline_script = """correct[0] = 'correct' if (answers['1_2_1'] == expect) else 'incorrect'"""
        problem = self.build_problem(answer=inline_script, expect="42")

        # Check results
        self.assert_grade(problem, '42', 'correct')
        self.assert_grade(problem, '0', 'incorrect')

    def test_inline_message(self):

        # Inline code can update the global messages list
        # to pass messages to the CorrectMap for a particular input
        # The code can also set the global overall_message (str)
        # to pass a message that applies to the whole response
        inline_script = textwrap.dedent("""
        messages[0] = "Test Message" 
        overall_message = "Overall message"
        """)
        problem = self.build_problem(answer=inline_script)

        input_dict = {'1_2_1': '0'}
        correctmap = problem.grade_answers(input_dict)

        # Check that the message for the particular input was received
        input_msg = correctmap.get_msg('1_2_1')
        self.assertEqual(input_msg, "Test Message")

        # Check that the overall message (for the whole response) was received
        overall_msg = correctmap.get_overall_message()
        self.assertEqual(overall_msg, "Overall message")


    def test_function_code_single_input(self):

        # For function code, we pass in these arguments:
        # 
        #   'expect' is the expect attribute of the <customresponse>
        #
        #   'answer_given' is the answer the student gave (if there is just one input)
        #       or an ordered list of answers (if there are multiple inputs)
        #   
        #
        # The function should return a dict of the form 
        # { 'ok': BOOL, 'msg': STRING }
        #
        script = textwrap.dedent("""
            def check_func(expect, answer_given):
                return {'ok': answer_given == expect, 'msg': 'Message text'}
        """)

        problem = self.build_problem(script=script, cfn="check_func", expect="42")

        # Correct answer
        input_dict = {'1_2_1': '42'}
        correct_map = problem.grade_answers(input_dict)

        correctness = correct_map.get_correctness('1_2_1')
        msg = correct_map.get_msg('1_2_1')

        self.assertEqual(correctness, 'correct')
        self.assertEqual(msg, "Message text")

        # Incorrect answer
        input_dict = {'1_2_1': '0'}
        correct_map = problem.grade_answers(input_dict)

        correctness = correct_map.get_correctness('1_2_1')
        msg = correct_map.get_msg('1_2_1')

        self.assertEqual(correctness, 'incorrect')
        self.assertEqual(msg, "Message text")

    def test_function_code_multiple_input_no_msg(self):

        # Check functions also have the option of returning
        # a single boolean value 
        # If true, mark all the inputs correct
        # If false, mark all the inputs incorrect
        script = textwrap.dedent("""
            def check_func(expect, answer_given):
                return (answer_given[0] == expect and
                        answer_given[1] == expect)
        """)

        problem = self.build_problem(script=script, cfn="check_func", 
                                    expect="42", num_inputs=2)

        # Correct answer -- expect both inputs marked correct
        input_dict = {'1_2_1': '42', '1_2_2': '42'}
        correct_map = problem.grade_answers(input_dict)

        correctness = correct_map.get_correctness('1_2_1')
        self.assertEqual(correctness, 'correct')

        correctness = correct_map.get_correctness('1_2_2')
        self.assertEqual(correctness, 'correct')

        # One answer incorrect -- expect both inputs marked incorrect
        input_dict = {'1_2_1': '0', '1_2_2': '42'}
        correct_map = problem.grade_answers(input_dict)

        correctness = correct_map.get_correctness('1_2_1')
        self.assertEqual(correctness, 'incorrect')

        correctness = correct_map.get_correctness('1_2_2')
        self.assertEqual(correctness, 'incorrect')


    def test_function_code_multiple_inputs(self):

        # If the <customresponse> has multiple inputs associated with it,
        # the check function can return a dict of the form:
        # 
        # {'overall_message': STRING,
        #  'input_list': [{'ok': BOOL, 'msg': STRING}, ...] }
        # 
        # 'overall_message' is displayed at the end of the response
        #
        # 'input_list' contains dictionaries representing the correctness
        #           and message for each input.
        script = textwrap.dedent("""
            def check_func(expect, answer_given):
                check1 = (int(answer_given[0]) == 1)
                check2 = (int(answer_given[1]) == 2)
                check3 = (int(answer_given[2]) == 3)
                return {'overall_message': 'Overall message',
                        'input_list': [
                            {'ok': check1,  'msg': 'Feedback 1'},
                            {'ok': check2,  'msg': 'Feedback 2'},
                            {'ok': check3,  'msg': 'Feedback 3'} ] }
            """)

        problem = self.build_problem(script=script, 
                                    cfn="check_func", num_inputs=3)

        # Grade the inputs (one input incorrect)
        input_dict = {'1_2_1': '-999', '1_2_2': '2', '1_2_3': '3' }
        correct_map = problem.grade_answers(input_dict)

        # Expect that we receive the overall message (for the whole response)
        self.assertEqual(correct_map.get_overall_message(), "Overall message")

        # Expect that the inputs were graded individually
        self.assertEqual(correct_map.get_correctness('1_2_1'), 'incorrect')
        self.assertEqual(correct_map.get_correctness('1_2_2'), 'correct')
        self.assertEqual(correct_map.get_correctness('1_2_3'), 'correct')

        # Expect that we received messages for each individual input
        self.assertEqual(correct_map.get_msg('1_2_1'), 'Feedback 1')
        self.assertEqual(correct_map.get_msg('1_2_2'), 'Feedback 2')
        self.assertEqual(correct_map.get_msg('1_2_3'), 'Feedback 3')


    def test_multiple_inputs_return_one_status(self):
        # When given multiple inputs, the 'answer_given' argument
        # to the check_func() is a list of inputs
        #
        # The sample script below marks the problem as correct
        # if and only if it receives answer_given=[1,2,3]
        # (or string values ['1','2','3'])
        #
        # Since we return a dict describing the status of one input,
        # we expect that the same 'ok' value is applied to each
        # of the inputs.
        script = textwrap.dedent("""
            def check_func(expect, answer_given):
                check1 = (int(answer_given[0]) == 1)
                check2 = (int(answer_given[1]) == 2)
                check3 = (int(answer_given[2]) == 3)
                return {'ok': (check1 and check2 and check3),  
                        'msg': 'Message text'}
            """)

        problem = self.build_problem(script=script, 
                                    cfn="check_func", num_inputs=3)

        # Grade the inputs (one input incorrect)
        input_dict = {'1_2_1': '-999', '1_2_2': '2', '1_2_3': '3' }
        correct_map = problem.grade_answers(input_dict)

        # Everything marked incorrect
        self.assertEqual(correct_map.get_correctness('1_2_1'), 'incorrect')
        self.assertEqual(correct_map.get_correctness('1_2_2'), 'incorrect')
        self.assertEqual(correct_map.get_correctness('1_2_3'), 'incorrect')

        # Grade the inputs (everything correct)
        input_dict = {'1_2_1': '1', '1_2_2': '2', '1_2_3': '3' }
        correct_map = problem.grade_answers(input_dict)

        # Everything marked incorrect
        self.assertEqual(correct_map.get_correctness('1_2_1'), 'correct')
        self.assertEqual(correct_map.get_correctness('1_2_2'), 'correct')
        self.assertEqual(correct_map.get_correctness('1_2_3'), 'correct')

        # Message is interpreted as an "overall message"
        self.assertEqual(correct_map.get_overall_message(), 'Message text')

    def test_script_exception(self):

        # Construct a script that will raise an exception
        script = textwrap.dedent("""
            def check_func(expect, answer_given):
                raise Exception("Test")
            """)

        problem = self.build_problem(script=script, cfn="check_func")

        # Expect that an exception gets raised when we check the answer
        with self.assertRaises(Exception):
            problem.grade_answers({'1_2_1': '42'})
    
    def test_invalid_dict_exception(self):

        # Construct a script that passes back an invalid dict format
        script = textwrap.dedent("""
            def check_func(expect, answer_given):
                return {'invalid': 'test'}
            """)

        problem = self.build_problem(script=script, cfn="check_func")

        # Expect that an exception gets raised when we check the answer
        with self.assertRaises(Exception):
            problem.grade_answers({'1_2_1': '42'})


class SchematicResponseTest(ResponseTest):
    from response_xml_factory import SchematicResponseXMLFactory
    xml_factory_class = SchematicResponseXMLFactory

    def test_grade(self):

        # Most of the schematic-specific work is handled elsewhere
        # (in client-side JavaScript)
        # The <schematicresponse> is responsible only for executing the
        # Python code in <answer> with *submission* (list)
        # in the global context.

        # To test that the context is set up correctly,
        # we create a script that sets *correct* to true
        # if and only if we find the *submission* (list)
        script="correct = ['correct' if 'test' in submission[0] else 'incorrect']"
        problem = self.build_problem(answer=script)

        # The actual dictionary would contain schematic information
        # sent from the JavaScript simulation
        submission_dict = {'test': 'test'}
        input_dict = { '1_2_1': json.dumps(submission_dict) }
        correct_map = problem.grade_answers(input_dict)

        # Expect that the problem is graded as true
        # (That is, our script verifies that the context
        # is what we expect)
        self.assertEqual(correct_map.get_correctness('1_2_1'), 'correct')

class AnnotationResponseTest(ResponseTest):
    from response_xml_factory import AnnotationResponseXMLFactory
    xml_factory_class = AnnotationResponseXMLFactory

    def test_grade(self):
        (correct, partially, incorrect) = ('correct', 'partially-correct', 'incorrect')

        answer_id = '1_2_1'
        options = (('x', correct),('y', partially),('z', incorrect))
        make_answer = lambda option_ids: {answer_id: json.dumps({'options': option_ids })}

        tests = [
            {'correctness': correct, 'points': 2,'answers': make_answer([0]) },
            {'correctness': partially, 'points': 1, 'answers': make_answer([1]) },
            {'correctness': incorrect, 'points': 0, 'answers': make_answer([2]) },
            {'correctness': incorrect, 'points': 0, 'answers': make_answer([0,1,2]) },
            {'correctness': incorrect, 'points': 0, 'answers': make_answer([]) },
            {'correctness': incorrect, 'points': 0, 'answers': make_answer('') },
            {'correctness': incorrect, 'points': 0, 'answers': make_answer(None) },
            {'correctness': incorrect, 'points': 0, 'answers': {answer_id: 'null' } },
        ]

        for (index, test) in enumerate(tests):
            expected_correctness = test['correctness']
            expected_points = test['points']
            answers = test['answers']

            problem = self.build_problem(options=options)
            correct_map = problem.grade_answers(answers)
            actual_correctness = correct_map.get_correctness(answer_id)
            actual_points = correct_map.get_npoints(answer_id)

            self.assertEqual(expected_correctness, actual_correctness,
                             msg="%s should be marked %s" % (answer_id, expected_correctness))
            self.assertEqual(expected_points, actual_points,
                             msg="%s should have %d points" % (answer_id, expected_points))
