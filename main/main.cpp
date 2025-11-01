#include "main/parse_data.h"
#include "main/writers.h"
#include "nohlman/json.hpp"
#include "object_tracking/data_types/pose_2d.h"
#include "object_tracking/object_tracker.h"
#include "object_tracking/data_types/objects_types.h"
#include "interpolation/interpolate_vector.h"
#include <string.h>
#include <fstream>

static std::string Dirname(const std::string &path)
{
  auto pos = path.find_last_of("/\\");
  if (pos == std::string::npos)
    return std::string{"."};
  return path.substr(0, pos);
}

int main(int argc, char **argv)
{
  std::vector<TimedRobotPose> robot_poses{};
  std::vector<TimedDetectionPoses> detections{};
  // Read input JSON (path from argv[1] if provided, otherwise default)
  std::string input_path = (argc > 1) ? std::string(argv[1]) : std::string("main/data.json");
  nlohmann::json data_json = ReadJson(input_path);
  ParseRobotData(robot_poses, data_json);
  ParseDetectionData(detections, data_json);

  std::vector<double> time_data_detection{};
  std::vector<double> time_data_robot{};
  std::vector<double> data_x_robot{};
  std::vector<double> data_y_robot{};
  std::vector<double> data_orientation_robot{};

  for (const auto &timed_detection : detections)
  {
    time_data_detection.push_back(timed_detection.time);
  }

  for (const auto &timed_pose : robot_poses)
  {
    time_data_robot.push_back(timed_pose.time);
    data_x_robot.push_back(timed_pose.pose_2d.x);
    data_y_robot.push_back(timed_pose.pose_2d.y);
    data_orientation_robot.push_back(timed_pose.pose_2d.orientation);
  }

  std::vector<double> data_x_interp_vector = InterpolateDoubleVector(time_data_robot, data_x_robot, time_data_detection);
  std::vector<double> data_y_interp_vector = InterpolateDoubleVector(time_data_robot, data_y_robot, time_data_detection);
  std::vector<double> data_orientation_interp_vector = InterpolateDoubleVector(time_data_robot, data_orientation_robot, time_data_detection);

  std::vector<TimedRobotPose> robot_poses_interp{};
  for (int i{0}; i < time_data_detection.size(); i++)
  {
    robot_poses_interp.push_back(
        TimedRobotPose{time_data_detection[i],
                       Pose2D{float(data_x_interp_vector[i]),
                              float(data_y_interp_vector[i]),
                              float(data_orientation_interp_vector[i])}});
  }

  ObjectTracker object_tracker{};

  // Write intermediate outputs next to the input file
  std::string base_dir = Dirname(input_path);
  WriteOutRobotPoses(robot_poses_interp, base_dir + "/robot_poses.json");
  WriteOutDetectionPoses(detections, base_dir + "/detections.json");

  object_tracker.Update(robot_poses_interp, detections);
  object_tracker.ProduceDetectionPosesInGlobalCs();
  auto results = object_tracker.GetLoadCarriersPosesInCsGlobal();

  WriteOutDetectionPosesInCsGloabl(results, base_dir + "/detections_output.json");

  return 0;
}
