//
// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
//

import { AudioStreamFormat, PullAudioInputStream, PullAudioInputStreamCallback, PushAudioInputStream } from "../Exports";

/**
 * Represents audio input stream used for custom audio input configurations.
 */
export abstract class AudioInputStream {

    protected constructor() { }

    /**
     * Creates a memory backed PushAudioInputStream with the specified audio format.
     * @param format The audio data format in which audio will be written to the push audio stream's write() method (currently only support 16Khz 16bit mono PCM).
     * @return The audio input stream being created.
     */
    public static createPushStream(format?: AudioStreamFormat): PushAudioInputStream {
        return PushAudioInputStream.create(format);
    }

    /**
     * Creates a PullAudioInputStream that delegates to the specified callback interface for read() and close() methods.
     * @param callback The custom audio input object, derived from PullAudioInputStreamCallback
     * @param format The audio data format in which audio will be returned from the callback's read() method (currently only support 16Khz 16bit mono PCM).
     * @return The audio input stream being created.
     */
    public static createPullStream(callback: PullAudioInputStreamCallback, format: AudioStreamFormat): PullAudioInputStream {
        return PullAudioInputStream.create(callback, format);
    }

    /**
     * Explicitly frees any external resource attached to the object
     */
    public abstract close(): void;
}