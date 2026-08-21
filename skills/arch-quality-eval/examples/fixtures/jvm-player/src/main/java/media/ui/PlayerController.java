package media.ui;

import media.domain.PlaybackService;
import media.infra.MediaStore;

public final class PlayerController {
  private final PlaybackService playback;
  private final MediaStore store;

  public PlayerController(PlaybackService playback, MediaStore store) {
    this.playback = playback;
    this.store = store;
  }

  public void play(String mediaId) {
    if (store.exists(mediaId)) {
      playback.play(mediaId);
    }
  }
}
