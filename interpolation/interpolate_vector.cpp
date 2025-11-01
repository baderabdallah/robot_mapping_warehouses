#include "interpolation/interpolate_vector.h"
#include "interpolation/interp.hpp"

std::vector<double> InterpolateDoubleVector(std::vector<double> &time, std::vector<double> &data, std::vector<double> &time_reference)
{
    std::vector<double> data_interp{};
    double *time_array = &time[0];
    std::size_t time_size = time.size();
    double *data_array = &data[0];
    std::size_t time_reference_size = time_reference.size();
    double *time_reference_array = &time_reference[0];

    double *data_interp_array = interp_linear(1, time_size, time_array, data_array,
                                              time_reference_size, time_reference_array);
    data_interp.reserve(time_reference_size);

    for (std::size_t i{0}; i < time_reference_size; i++)
    {
        data_interp.push_back(data_interp_array[i]);
    }

    return data_interp;
}
