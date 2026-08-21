#pragma once

namespace media::domain {

class PlaybackService {
 public:
  void play(const char* media_id);
};

}  // namespace media::domain
