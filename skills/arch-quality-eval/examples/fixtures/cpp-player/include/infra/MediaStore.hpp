#pragma once

namespace media::infra {

class MediaStore {
 public:
  bool exists(const char* media_id) const;
};

}  // namespace media::infra
