"""
:Date: May 2011
:Author: AAB, berger at cenix-bioscience dot com
"""
from thelma import LogEvent
from thelma import ThelmaLog
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['EventRecording',
           ]


class EventRecording(object):
    """
    This is the abstract base class for all classes recording errors
    and events.
    """
    #: A name passed by the object used to identify the log.
    NAME = None
    #: All events having a level equal or larger than this will be regarded as
    #: error
    ERROR_THRESHOLD = ThelmaLog.ERROR_THRESHOLD
    #
    logging_level = None
    """
    Available options are:

        + logging.CRITICAL  :       severity 50
        + logging.ERROR     :       severity 40
        + logging.WARNING   :       severity 30
        + logging.INFO      :       severity 20
        + logging.DEBUG     :       severity 10
        + logging.NOTSET    :
          (parent logger level or all events (if no parent available))

        All log events having at least the given severity will be logged.
        It can be adjusted with the :func:`set_log_ecording_level` function.
    """ #pylint: disable=W0105

    def __init__(self, log,
                 logging_level=None,
                 add_default_handlers=False):
        """
        Constructor:

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`ThelmaLog`
        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING
        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        #: The log recording errors and events.
        self.log = None

        if log is None:
            # This is to fool pylint. If we use getLogger directly, it thinks
            # the logger is a logging.Logger instance and complains about
            # missing method names.
            get_fn = getattr(logging, 'getLogger')
            self.log = get_fn(self.__class__.__module__ + '.' +
                              self.__class__.__name__)
            if not logging_level is None:
                self.log.setLevel(logging_level)
        else:
            self.log = log

        # TODO: do we still need that?
        if add_default_handlers and len(self.log.handlers) < 1:
            self._add_default_handlers()
#        elif log is None and not add_default_handlers:
#            self.__add_null_handler()

        #: The errors that have occurred within the tool.
        self._error_count = 0

        #: As soon this is set to *True* errors and warnings will not be
        #: recorded anymore.
        #: However, the execution of running methods is still aborted.
        #: Use :func:`disable_error_and_warning_recording` to activate.
        self.__disable_err_warn_rec = False
        #: If this is set to *True* the execution of methods is aborted
        #: silently.
        self._abort_execution = False

    def disable_error_and_warning_recording(self):
        """
        Use this method to disable recording of error and warning events.
        In cases of errors, method execution will still be aborted, though.
        """
        self.__disable_err_warn_rec = True

    def get_messages(self, logging_level=logging.WARNING):
        """
        Returns the log's messages having the given severity level or more.
        """
        return self.log.get_messages(logging_level)

    def has_errors(self):
        """
        Checks if the log has recorded errors (ThelmaLog types: ERROR and
        CRITICAL).

        :return: 0 (\'False\') if the parsing was completed without errors
                 or the number of errors detected (\'True\')
        :rtype: :class:`int` (:class:`boolean`)
        """
        return (self._error_count > 0 or self._abort_execution)

    def reset_log(self):
        """
        Replaces the current log by a new one.
        """
        self.log.reset()
        self._error_count = 0

    def set_log_recording_level(self, log_level):
        """
        Sets the threshold :py:attr:`LOGGING_LEVEL` of the log.

        :param log_level: the desired minimum log level
        :type log_level: int (or LOGGING_LEVEL as
                         imported from :py:mod:`logging`)
        """
        self.log.level = log_level

    def _add_default_handlers(self):
        """
        Generates handlers that are added automatically upon initialisation.
        """
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        self.add_log_handler(stream_handler)

    def __add_null_handler(self):
        """
        Adds a null handler to the object (if not log has passed and the
        default handlers are not to be initialised).
        """
        self.add_log_handler(logging.NullHandler())

    def add_critical_error(self, error_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: CRITICAL), adds it to the :py:attr:`log` (class:`ThelmaLog`)
        and raises the log's :attr:`error_count` of the log.

        :param error_msg: an error message
        :type error_msg: :class:`string`

        """
        evt = LogEvent(self.NAME, error_msg)
        if not self.__disable_err_warn_rec: self.log.add_critical(evt)
        self._adjust_error_count(logging.CRITICAL)

    def add_error(self, error_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: ERROR), adds it to the :py:attr:`log` (class:`ThelmaLog`)
        and raises the log's :attr:`error_count` of the log.

        :param error_msg: an error message
        :type error_msg: :class:`string`
        """
        evt = LogEvent(self.NAME, error_msg)
        if not self.__disable_err_warn_rec: self.log.add_error(evt)
        self._adjust_error_count(logging.ERROR)

    def add_warning(self, warning_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: WARNING) and adds it to the :py:attr:`log` (class:`ThelmaLog`).

        :param warning_msg: a warning message
        :type warning_msg: :class:`string`
        """
        evt = LogEvent(self.NAME, warning_msg,
                       is_exception=False)
        if not self.__disable_err_warn_rec: self.log.add_warning(evt)
        self._adjust_error_count(logging.WARNING)

    def add_info(self, info_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: INFO) and adds it to the :py:attr:`log` (class:`ThelmaLog`).

        :param info_msg: a warning message
        :type info_msg: :class:`string`
        """
        evt = LogEvent(self.NAME, info_msg, is_exception=False)
        self.log.add_info(evt)
        self._adjust_error_count(logging.INFO)

    def add_debug(self, debug_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: DEBUG) and adds it to the :py:attr:`log` (class:`ThelmaLog`).

        :param debug_msg: a warning message
        :type debug_msg: :class:`string`
        """
        evt = LogEvent(self.NAME, debug_msg, is_exception=False)
        self.log.add_debug(evt)
        self._adjust_error_count(logging.DEBUG)

    def add_log_event(self, log_event, log_level):
        """
        Adds an already existing LogEvent object to the :attr:`log`.

        :param log_event: A log event.
        :type log_event: :class:`log_event`
        :param log_level: The severity of the event.
        :type log_level: :class:`int` (logging severity value).
        """
        self._adjust_error_count(log_level)
        self.log.add_record(log_level, log_event.tostring())

    def _adjust_error_count(self, logging_level):
        """
        Increases the tools error count if the severity of a logging level
        is equal or above the :attr:`ERROR_THRESHOLD`.
        """
        if logging_level >= self.ERROR_THRESHOLD and \
                                            not self.__disable_err_warn_rec:
            self._error_count += 1
        self._abort_execution = True

    def add_log_handlers(self, handlers):
        """
        Adds handlers to the parsing log.

        :param handlers: the desired handlers
        :type handlers: list of :py:class:`logging.Handler` objects
        """
        for handler in handlers:
            self.log.addHandler(handler)

    def add_log_handler(self, handler):
        """
        Adds handlers to the parsing log.

        :param handlers: the desired handler
        :type handlers: list of :py:class:`logging.Handler` objects
        """
        self.log.addHandler(handler)

    def _check_input_class(self, name, obj, exp_class):
        """
        Checks whether a objects has the expected class and raises an
        error, if applicable.

        :param name: The name under which the object shall be referenced.
        :type name: :class:`str`

        :param obj: The object to be tested.
        :type obj: any

        :param exp_class: The expected class.
        :type exp_class: any
        """
        if not isinstance(obj, exp_class):
            msg = 'The %s must be a %s object (obtained: %s).' \
                  % (name, exp_class.__name__, obj.__class__.__name__)
            self.add_error(msg)
            return False
        return True

    def _run_and_record_error(self, meth, base_msg, error_types=None, **kw):
        """
        Convenience method that runs a method and catches errors of the
        specified class. The error messages are recorded along with the
        base msg.

        :param meth: The method to be called.

        :param base_msg: This message is put in front of the potential error
            message.
        :type base_msg: :class:`str`

        :param error_types: Error classes that shall be caught.
        :type error_types: iterable
        :default error_type: *None* (catches AttributeError, ValueError and
            TypeError)

        :return: The method return value or *None* (in case of exception)
        """
        filler = ': '
        if base_msg.endswith(filler):
            filler = ''
        elif base_msg.endswith(':'):
            filler = ' '
        base_msg += filler
        if error_types is None:
            error_types = set(ValueError, TypeError, AttributeError)

        try:
            return_value = meth(**kw)
        except StandardError as e:
            if e.__class__ in error_types:
                self.add_error(base_msg + e)
            else:
                raise e
        else:
            return return_value
