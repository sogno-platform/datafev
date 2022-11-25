# The datafev framework

# Copyright (C) 2022,
# Institute for Automation of Complex Power Systems (ACS),
# E.ON Energy Research Center (E.ON ERC),
# RWTH Aachen University

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


def departure_routine(ts, fleet):
    """
    This routine is executed for EVs leaving the charger clusters.

    Parameters
    ----------
    ts : datetime
        Current time.
    fleet : datahandling.fleet
        EV fleet object.

    Returns
    -------
    None.

    """

    outgoing_vehicles = fleet.outgoing_vehicles_at(ts)

    # Managing the leaving EVs
    for ev in outgoing_vehicles:

        if ev.admitted == True:

            if ev.reserved == True:

                cu = ev.connected_cu
                cu.disconnect(ts)

                cc = ev.connected_cc
                cc.unreserve(ts, ev.reservation_id)
                cc.enter_data_of_outgoing_vehicle(ts, ev)

                ev.reservation_id = None
