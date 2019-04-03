# Copyright (c) Microsoft. All rights reserved.
# See https://aka.ms/csspeech/license201809 for the full license information.

import pytest

import azure.cognitiveservices.speech as msspeech

from .utils import (_TestCallback, _check_callbacks, _check_sr_result, _wait_for_event)

speech_config_types = (msspeech.SpeechConfig, msspeech.translation.SpeechTranslationConfig)
recognizer_types = (msspeech.SpeechRecognizer, msspeech.translation.TranslationRecognizer,
                    msspeech.intent.IntentRecognizer)

@pytest.mark.parametrize('speech_input,', ['weather', 'lamp'], indirect=True)
def test_recognize_once(from_file_speech_reco_with_callbacks, speech_input):
    reco, callbacks = from_file_speech_reco_with_callbacks()

    result = reco.recognize_once()
    _check_sr_result(result, speech_input, 0)
    _wait_for_event(callbacks, 'session_stopped')
    _check_callbacks(callbacks)

    desired_result_str = 'SpeechRecognitionResult(' \
            'result_id={}, text="{}", reason=ResultReason.RecognizedSpeech)'.format(
                    result.result_id, speech_input.transcription[0])

    assert str(result) == desired_result_str

@pytest.mark.parametrize('speech_input,', ['weather'], indirect=True)
def test_recognize_async(from_file_speech_reco_with_callbacks, speech_input):
    reco, callbacks = from_file_speech_reco_with_callbacks()

    future = reco.recognize_once_async()
    result = future.get()

    _check_sr_result(result, speech_input, 0)
    _wait_for_event(callbacks, 'session_stopped')
    _check_callbacks(callbacks)

    # verify that the second call to get from future fails orderly
    # error message is platform-dependent
    with pytest.raises(RuntimeError, match="Operation not permitted on an object without an "
            "associated state|std::future_error: No associated state|no state"):
        future.get()


@pytest.mark.parametrize('speech_input,', ['silencehello'], indirect=True)
def test_speech_recognition_with_custom_endpoint(subscription, speech_input, speech_region):
    initial_silence_timeout_ms = 1 * 1e3
    template = "wss://{}.stt.speech.microsoft.com/speech/recognition" \
            "/conversation/cognitiveservices/v1?initialSilenceTimeoutMs={:d}"
    speech_config = msspeech.SpeechConfig(subscription=subscription,
            endpoint=template.format(speech_region, int(initial_silence_timeout_ms)))

    audio_config = msspeech.audio.AudioConfig(filename=speech_input.path)
    # Creates a speech recognizer using a file as audio input.
    # The default language is "en-us".
    reco = msspeech.SpeechRecognizer(speech_config, audio_config)

    future = reco.recognize_once_async()
    result = future.get()

    assert msspeech.ResultReason.NoMatch == result.reason
    assert msspeech.NoMatchReason.InitialSilenceTimeout == result.no_match_details.reason


@pytest.mark.xfail(reason='flaky')
@pytest.mark.parametrize('speech_input,', ['batman'], indirect=True)
def test_recognize_once_multiple(from_file_speech_reco_with_callbacks, speech_input):
    reco, callbacks = from_file_speech_reco_with_callbacks()

    for utterance_index in range(2):
        result = reco.recognize_once()
        _check_sr_result(result, speech_input, utterance_index)


@pytest.mark.parametrize('speech_input,', ['weather'], indirect=True)
def test_multiple_callbacks(from_file_speech_reco_with_callbacks, speech_input):
    reco, callbacks = from_file_speech_reco_with_callbacks()

    # connect a second callback to two signals
    other_session_started_cb = _TestCallback('In OTHER session_started callback')
    other_recognized_cb = _TestCallback('In OTHER recognized callback')
    reco.session_started.connect(other_session_started_cb)
    reco.recognized.connect(other_recognized_cb)

    result = reco.recognize_once()

    _check_sr_result(result, speech_input, 0)
    _wait_for_event(callbacks, 'session_stopped')
    _check_callbacks(callbacks)
    assert other_recognized_cb.num_calls == 1


def test_config_construction_kwargs():
    speech_config = msspeech.SpeechConfig(subscription="somesubscription", region="someregion")
    assert speech_config


@pytest.mark.parametrize("config_type", speech_config_types)
def test_speech_config_default_constructor(config_type):
    # from_subscription
    speech_config = config_type(subscription="somesubscription", region="someregion")
    assert speech_config
    assert "somesubscription" == speech_config.subscription_key
    assert "someregion" == speech_config.region

    # from_subscription, positional args
    speech_config = config_type("somesubscription", "someregion")
    assert speech_config
    assert "somesubscription" == speech_config.subscription_key
    assert "someregion" == speech_config.region

    # from_authorization_token
    speech_config = config_type(auth_token="sometoken", region="someregion")
    assert speech_config
    assert "" == speech_config.subscription_key
    assert "sometoken" == speech_config.authorization_token
    assert "someregion" == speech_config.region

    # from_endpoint
    speech_config = config_type(endpoint="someendpoint", subscription="somesubscription")
    assert speech_config
    assert "somesubscription" == speech_config.subscription_key
    assert "" == speech_config.region
    assert "someendpoint" == speech_config.get_property(msspeech.PropertyId.SpeechServiceConnection_Endpoint)

    # from_subscription, with language
    speech_config = config_type(subscription="somesubscription", region="someregion",
                                speech_recognition_language='zh-CN')
    assert speech_config
    assert "somesubscription" == speech_config.subscription_key
    assert "someregion" == speech_config.region
    assert "zh-CN" == speech_config.speech_recognition_language

    # check correct error messages
    with pytest.raises(ValueError,
            match='either endpoint or region must be given along with a subscription key'):
        speech_config = config_type(subscription="somesubscription")

    with pytest.raises(ValueError,
            match='either subscription key or authorization token must be given along with a region'):
        speech_config = config_type(region="someregion")

    with pytest.raises(ValueError,
            match='either endpoint or region must be given along with a subscription key'):
        speech_config = config_type(subscription="somesubscription")

    with pytest.raises(ValueError,
            match='cannot construct SpeechConfig with both region and endpoint information'):
        speech_config = config_type(endpoint="someendpoint", region="someregion")

    with pytest.raises(ValueError,
            match='cannot construct SpeechConfig with both region and endpoint information'):
        speech_config = config_type(endpoint="someendpoint", region="someregion",
            subscription="somesubscription")

    with pytest.raises(ValueError, match='cannot construct SpeechConfig with the given arguments'):
        speech_config = config_type()

    with pytest.raises(ValueError, match='subscription key must be specified along with an endpoint'):
        speech_config = config_type(endpoint='someendpoint')

    # check that all nonsupported construction methods raise
    from itertools import product
    for subscription, region, endpoint, auth_token in product((None, "somekey"),
            (None, "someregion"),
            (None, "someendpoint"),
            (None, "sometoken")):
        if ((subscription and region and not endpoint and not auth_token) or
                (subscription and not region and endpoint and not auth_token) or
                (not subscription and region and not endpoint and auth_token)):

            speech_config = config_type(subscription=subscription,
                    region=region,
                    endpoint=endpoint,
                    auth_token=auth_token)
            assert speech_config
        else:
            with pytest.raises(ValueError):
                speech_config = config_type(subscription=subscription,
                        region=region,
                        endpoint=endpoint,
                        auth_token=auth_token)


@pytest.mark.parametrize("config_type", speech_config_types)
def test_config_system_language(config_type):
    speech_config = config_type(subscription="somesubscription", region="someregion",
                                speech_recognition_language='zh-CN')
    value = speech_config._impl.get_property("SPEECHSDK-SPEECH-CONFIG-SYSTEM-LANGUAGE")
    assert "Python" == value


@pytest.mark.parametrize('speech_input,', ['weather'], indirect=True)
def test_canceled_result(speech_input):
    invalid_cfg = msspeech.SpeechConfig(endpoint="invalid", subscription="invalid")
    audio_config = msspeech.audio.AudioConfig(filename=speech_input.path)

    reco = msspeech.SpeechRecognizer(invalid_cfg, audio_config)

    result = reco.recognize_once_async().get()

    assert msspeech.ResultReason.Canceled == result.reason

    cancellation_details = result.cancellation_details
    assert msspeech.CancellationReason.Error == cancellation_details.reason
    assert 'Runtime error: Failed to create transport request.' == cancellation_details.error_details

    assert "ResultReason.Canceled" == str(result.reason)
    assert 'CancellationDetails(reason=CancellationReason.Error, error_details="Runtime error: ' \
            'Failed to create transport request.")' == str(result.cancellation_details)


@pytest.mark.parametrize('speech_input,', ['weather'], indirect=True)
def test_bad_language_config(subscription, speech_input, speech_region):
    bad_lang_cfg = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    bad_lang_cfg.speech_recognition_language = "bad language"
    assert "bad language" == bad_lang_cfg.speech_recognition_language
    audio_config = msspeech.audio.AudioConfig(filename=speech_input.path)

    reco = msspeech.SpeechRecognizer(bad_lang_cfg, audio_config)

    result = reco.recognize_once_async().get()

    assert msspeech.ResultReason.Canceled == result.reason

    cancellation_details = result.cancellation_details
    assert msspeech.CancellationReason.Error == cancellation_details.reason
    assert 'WebSocket Upgrade failed with HTTP status code: 505' == cancellation_details.error_details


@pytest.mark.parametrize('speech_input,', ['silence'], indirect=True)
def test_no_match_result(from_file_speech_reco_with_callbacks, speech_input):
    reco, callbacks = from_file_speech_reco_with_callbacks()

    result = reco.recognize_once_async().get()

    assert msspeech.ResultReason.NoMatch == result.reason
    assert result.cancellation_details is None
    details = result.no_match_details
    assert msspeech.NoMatchReason.InitialSilenceTimeout == details.reason

    assert "NoMatchDetails(reason=NoMatchReason.InitialSilenceTimeout)" == str(result.no_match_details)


def test_speech_config_properties(subscription, speech_region):
    speech_config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)

    assert subscription == speech_config.subscription_key
    assert "" == speech_config.authorization_token
    assert "" == speech_config.endpoint_id
    assert speech_region == speech_config.region
    assert "" == speech_config.speech_recognition_language

    assert isinstance(speech_config.output_format, msspeech.OutputFormat)
    assert speech_config.output_format == msspeech.OutputFormat.Simple


@pytest.mark.parametrize('speech_input,', ['silence'], indirect=True)
def test_speech_recognizer_default_constructor(speech_input):
    """test that the default argument for AudioConfig is correct"""
    speech_config = msspeech.SpeechConfig(subscription="subscription", region="some_region")
    audio_config = msspeech.audio.AudioConfig(filename=speech_input.path)

    reco = msspeech.SpeechRecognizer(speech_config, audio_config)
    assert isinstance(reco, msspeech.SpeechRecognizer)


@pytest.mark.parametrize('speech_input,', ['silence'], indirect=True)
def test_translation_recognizer_default_constructor(speech_input):
    """test that the default argument for AudioConfig is correct"""
    speech_config = msspeech.translation.SpeechTranslationConfig(subscription="subscription", region="some_region")
    audio_config = msspeech.audio.AudioConfig(filename=speech_input.path)

    speech_config.speech_recognition_language = "en-US"
    speech_config.add_target_language('de')

    reco = msspeech.translation.TranslationRecognizer(speech_config, audio_config)
    assert isinstance(reco, msspeech.translation.TranslationRecognizer)

    assert "" == reco.authorization_token
    reco.authorization_token = "mytoken"
    assert "mytoken" == reco.authorization_token

    assert isinstance(reco.properties, msspeech.PropertyCollection)


@pytest.mark.parametrize('speech_input,', ['silence'], indirect=True)
def test_speech_recognizer_properties(speech_input):
    speech_config = msspeech.SpeechConfig(endpoint="myendpoint", subscription="mysubscription")
    audio_config = msspeech.audio.AudioConfig(filename=speech_input.path)

    assert "mysubscription" == speech_config.subscription_key
    assert "myendpoint" == speech_config.get_property(msspeech.PropertyId.SpeechServiceConnection_Endpoint)

    reco = msspeech.SpeechRecognizer(speech_config, audio_config)

    assert "myendpoint" == reco.properties.get_property(msspeech.PropertyId.SpeechServiceConnection_Endpoint)

    assert "" == reco.authorization_token
    reco.authorization_token = "mytoken"
    assert "mytoken" == reco.authorization_token

    assert reco.endpoint_id == ""


def test_speech_config_properties_setters():
    speech_config = msspeech.SpeechConfig(subscription="some_key", region="some_region")

    speech_config.speech_recognition_language = "de_de"
    assert "de_de" == speech_config.speech_recognition_language

    speech_config.endpoint_id = "x"
    assert "x" == speech_config.endpoint_id

    speech_config.authorization_token = "x"
    assert "x" == speech_config.authorization_token

    with pytest.raises(AttributeError, match='can\'t set attribute'):
        speech_config.region = "newregion"


def test_speech_config_properties_output_format_setters():
    speech_config = msspeech.SpeechConfig(subscription="some_key", region="some_region")

    speech_config.output_format = msspeech.OutputFormat.Simple
    assert msspeech.OutputFormat.Simple == speech_config.output_format

    speech_config.output_format = msspeech.OutputFormat.Detailed
    assert msspeech.OutputFormat.Detailed == speech_config.output_format

    with pytest.raises(TypeError, match='wrong type, must be OutputFormat'):
        speech_config.output_format = 0


def test_speech_config_property_ids():
    speech_config = msspeech.SpeechConfig(subscription="some_key", region="some_region")

    speech_config.set_property(msspeech.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, 'mytext')
    assert "mytext" == speech_config.get_property(msspeech.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse)

    speech_config.set_property(msspeech.PropertyId.SpeechServiceConnection_Endpoint, 'mytext')
    assert "mytext" == speech_config.get_property(msspeech.PropertyId.SpeechServiceConnection_Endpoint)

    error_message = 'property_id value must be PropertyId instance'
    with pytest.raises(TypeError, match=error_message):
        speech_config.set_property(1000, "bad_value")

    with pytest.raises(TypeError, match=error_message):
        speech_config.get_property(1000)


def test_speech_config_set_properties():
    speech_config = msspeech.SpeechConfig(subscription="some_key", region="some_region")

    properties = {
            msspeech.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse: 'true',
            msspeech.PropertyId.SpeechServiceConnection_Endpoint: 'myendpoint'}

    speech_config.set_properties(properties)

    assert "true" == speech_config.get_property(msspeech.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse)
    assert "myendpoint" == speech_config.get_property(msspeech.PropertyId.SpeechServiceConnection_Endpoint)

    with pytest.raises(TypeError, match='property_id value must be PropertyId instance'):
        speech_config.set_properties({1000: "bad_value"})


def test_keyword_recognition_model_constructor():
    model = msspeech.KeywordRecognitionModel(__file__)
    assert model

    with pytest.raises(ValueError, match="filename needs to be provided"):
        model = msspeech.KeywordRecognitionModel()


@pytest.mark.parametrize('speech_input,', ['silence'], indirect=True)
@pytest.mark.parametrize("recognizer_type", recognizer_types)
def test_speech_recognizer_constructor(speech_input, recognizer_type):
    if recognizer_type is msspeech.translation.TranslationRecognizer:
        speech_config = msspeech.translation.SpeechTranslationConfig(subscription='somesubscription', region='someregion')
        speech_config.speech_recognition_language = 'en-US'
        speech_config.add_target_language('de')
    else:
        speech_config = msspeech.SpeechConfig('somesubscription', 'someregion')

    audio_config = msspeech.audio.AudioConfig(filename=speech_input.path)

    with pytest.raises(TypeError,
            match=r"__init__\(\) missing 1 required positional argument: '(translation|speech)_config'"):
        reco = recognizer_type()

    with pytest.raises(ValueError, match="must be a Speech(Translation)?Config instance"):
        reco = recognizer_type(None)

    reco = recognizer_type(speech_config, audio_config)
    assert "somesubscription" == reco.properties.get_property(msspeech.PropertyId.SpeechServiceConnection_Key)
    assert "someregion" == reco.properties.get_property(msspeech.PropertyId.SpeechServiceConnection_Region)


@pytest.mark.usefixtures('skip_default_microphone')
@pytest.mark.parametrize("recognizer_type", recognizer_types)
def test_speech_recognizer_constructor_default_microphone(recognizer_type):
    if recognizer_type is msspeech.translation.TranslationRecognizer:
        speech_config = msspeech.translation.SpeechTranslationConfig(subscription='somesubscription', region='someregion')
        speech_config.speech_recognition_language = 'en-US'
        speech_config.add_target_language('de')
    else:
        speech_config = msspeech.SpeechConfig('somesubscription', 'someregion')

    reco = recognizer_type(speech_config)
    assert "somesubscription" == reco.properties.get_property(msspeech.PropertyId.SpeechServiceConnection_Key)
    assert "someregion" == reco.properties.get_property(msspeech.PropertyId.SpeechServiceConnection_Region)


@pytest.mark.parametrize("config_type", speech_config_types)
def test_speech_config_set_proxy(config_type):
    config = config_type("subscription", "region")
    config.set_proxy("hostname", 8888, "username", "very_secret123")

    assert "hostname" == config.get_property(msspeech.PropertyId.SpeechServiceConnection_ProxyHostName)
    assert "8888" == config.get_property(msspeech.PropertyId.SpeechServiceConnection_ProxyPort)
    assert "username" == config.get_property(msspeech.PropertyId.SpeechServiceConnection_ProxyUserName)
    assert "very_secret123" == config.get_property(msspeech.PropertyId.SpeechServiceConnection_ProxyPassword)
