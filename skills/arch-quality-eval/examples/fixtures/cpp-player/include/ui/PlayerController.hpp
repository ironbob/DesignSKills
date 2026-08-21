#pragma once

#include "domain/PlaybackService.hpp"
#include "infra/MediaStore.hpp"

namespace media::ui {

class PlayerController {
 public:
  PlayerController(domain::PlaybackService& playback, infra::MediaStore& store)
      : playback_(playback), store_(store) {}

  bool play(const char* media_id) {
    if (!store_.exists(media_id)) {
      return false;
    }
    playback_.play(media_id);
    return true;
  }

 private:
  domain::PlaybackService& playback_;
  infra::MediaStore& store_;
};

}  // namespace media::ui
