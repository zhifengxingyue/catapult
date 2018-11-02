# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re


class ParseError(Exception):

    def __init__(self, lineno, msg):
        super(ParseError, self).__init__('%d: %s' % (lineno, msg))


class Expectation(object):
    def __init__(self, reason, test, conditions, results):
        """Constructor for expectations.

    Args:
      reason: String that indicates the reason for disabling.
      test: String indicating which test is being disabled.
      conditions: List of tags indicating which conditions to disable for.
          Conditions are combined using logical and. Example: ['Mac', 'Debug']
      results: List of outcomes for test. Example: ['Skip', 'Pass']
    """
        assert isinstance(reason, basestring) or reason is None
        self._reason = reason
        assert isinstance(test, basestring)
        self._test = test
        self._conditions = frozenset(conditions)
        self._results = frozenset(results)

    def __eq__(self, other):
        return (self.reason == other.reason and self.test == other.test
                and self.conditions == other.conditions
                and self.results == other.results)

    @property
    def reason(self):
        return self._reason

    @property
    def test(self):
        return self._test

    @property
    def conditions(self):
        return self._conditions

    @property
    def results(self):
        return self._results


class TestExpectationParser(object):
    """Parse expectations data in TA/DA format.

  This parser covers the 'tagged' test lists format in:
      bit.ly/chromium-test-list-format

  Takes raw expectations data as a string read from the TA/DA expectation file
  in the format:

    # This is an example expectation file.
    #
    # tags: Mac Mac10.10 Mac10.11
    # tags: Win Win8

    crbug.com/123 [ Win ] benchmark/story [ Skip ]
    ...
  """

    TAG_TOKEN = '# tags:'
    _MATCH_STRING = r'^(?:(crbug.com/\d+) )?'  # The bug field (optional).
    _MATCH_STRING += r'(?:\[ (.+) \] )?'  # The label field (optional).
    _MATCH_STRING += r'(\S+) '  # The test path field.
    _MATCH_STRING += r'\[ ([^\[.]+) \]'  # The expectation field.
    _MATCH_STRING += r'(\s+#.*)?$'  # End comment (optional).
    MATCHER = re.compile(_MATCH_STRING)

    def __init__(self, raw_data):
        self._tags = []
        self._expectations = []
        self._parse_raw_expectation_data(raw_data)

    def _parse_raw_expectation_data(self, raw_data):
        for lineno, line in list(enumerate(raw_data.splitlines(), start=1)):
            # Handle metadata and comments.
            if line.startswith(self.TAG_TOKEN):
                for word in line[len(self.TAG_TOKEN):].split():
                    # Expectations must be after all tags are declared.
                    if self._expectations:
                        raise ParseError(lineno,
                                         'Tag found after first expectation.')
                    self._tags.append(word)
            elif line.startswith('#') or not line:
                continue  # Ignore, it is just a comment or empty.
            else:
                self._expectations.append(
                    self._parse_expectation_line(lineno, line, self._tags))

    def _parse_expectation_line(self, lineno, line, tags):
        match = self.MATCHER.match(line)
        if not match:
            raise ParseError(lineno, 'Syntax error: %s' % line)
        # Unused group is optional trailing comment.
        reason, raw_conditions, test, results, _ = match.groups()
        conditions = [c for c in raw_conditions.split()
                      ] if raw_conditions else []

        for c in conditions:
            if c not in tags:
                raise ParseError(lineno, 'Unknown tag value "%s"' % c)
        return Expectation(reason, test, conditions,
                           [r for r in results.split()])

    @property
    def expectations(self):
        return self._expectations

    @property
    def tags(self):
        return self._tags