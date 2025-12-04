import { useState, useEffect } from 'react';
import { Plus, X, Save } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Label } from './ui/label';
import { Slider } from './ui/slider';

type TAProfileStudentProps = {
  taId: number | null;
};

type CourseInterestLevel = 'high' | 'medium' | 'low' | null;

export default function TAProfileStudent({ taId }: TAProfileStudentProps) {
  const [loading, setLoading] = useState(false);
  const [taData, setTaData] = useState<any>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [workload, setWorkload] = useState([50]);
  const [courseInterests, setCourseInterests] = useState<Record<string, CourseInterestLevel>>({});

  const courses = [
    { code: 'COMP302', name: 'Programming Languages' },
    { code: 'COMP310', name: 'Operating Systems' },
    { code: 'COMP421', name: 'Database Systems' },
    { code: 'COMP424', name: 'Artificial Intelligence' },
    { code: 'COMP551', name: 'Applied Machine Learning' },
  ];

  useEffect(() => {
    if (!taId) return;

    setLoading(true);
    fetch(`/api/tas/${taId}`)
      .then(res => res.json())
      .then(data => {
        setTaData(data);
        setSkills(data.skills || []);
        const sliderVal = data.max_hours ? Math.round(((data.max_hours - 5) / 15) * 100) : 50;
        setWorkload([sliderVal]);

        // Initialize courseInterests for all courses
        const interests: Record<string, CourseInterestLevel> = {};
        courses.forEach(course => {
          interests[course.code] = data.course_interests?.[course.code] ?? null;
        });
        setCourseInterests(interests);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, [taId]);

  const getInterestColor = (interest: string) => {
    switch (interest) {
      case 'high': return 'bg-green-600 hover:bg-green-700';
      case 'medium': return 'bg-amber-600 hover:bg-amber-700';
      case 'low': return 'bg-neutral-400 hover:bg-neutral-500';
      default: return 'bg-neutral-400 hover:bg-neutral-500';
    }
  };

  if (loading || !taData) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Personal Info */}
      <Card>
        <CardHeader>
          <CardTitle>Personal Information</CardTitle>
          <CardDescription>Your basic profile details (read-only)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label className="text-xs text-neutral-500">Full Name</Label>
              <div className="text-sm text-neutral-900 mt-1">{taData.name}</div>
            </div>
            <div>
              <Label className="text-xs text-neutral-500">Program</Label>
              <div className="text-sm text-neutral-900 mt-1">{taData.program}</div>
            </div>
            <div>
              <Label className="text-xs text-neutral-500">Level</Label>
              <div className="text-sm text-neutral-900 mt-1">{taData.level}</div>
            </div>
            <div>
              <Label className="text-xs text-neutral-500">Max Hours/Week</Label>
              <div className="text-sm text-neutral-900 mt-1">{taData.max_hours}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Skills & Expertise */}
      <Card>
        <CardHeader>
          <CardTitle>Skills & Expertise</CardTitle>
          <CardDescription>Add relevant courses, programming languages, and technical skills</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2 p-4 border border-neutral-200 rounded-lg min-h-[100px]">
            {skills.map((skill, index) => (
              <Badge key={index} variant="outline" className="gap-1 bg-blue-50 text-blue-700 border-blue-200">
                {skill}
                <button onClick={() => setSkills(skills.filter((_, i) => i !== index))}>
                  <X className="w-3 h-3 cursor-pointer hover:text-blue-900" />
                </button>
              </Badge>
            ))}
          </div>
          <Button variant="outline" size="sm">
            <Plus className="w-4 h-4 mr-1" />
            Add Skill
          </Button>
        </CardContent>
      </Card>

      {/* Workload Preference */}
      <Card>
        <CardHeader>
          <CardTitle>Workload Preference</CardTitle>
          <CardDescription>How many hours per week are you willing to commit?</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-neutral-600">Low (5 hrs/week)</span>
              <span className="text-neutral-900">{Math.round((workload[0] / 100) * 15 + 5)} hrs/week</span>
              <span className="text-neutral-600">High (20 hrs/week)</span>
            </div>
            <Slider value={workload} onValueChange={setWorkload} max={100} step={1} className="w-full" />
          </div>
        </CardContent>
      </Card>

      {/* Course Preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Course Preferences</CardTitle>
          <CardDescription>Indicate your interest level for being a TA for each course</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {courses.map(course => {
              const interest = courseInterests[course.code] ?? null;
              return (
                <div key={course.code} className="flex items-center justify-between py-3 px-4 bg-neutral-50 rounded-lg">
                  <div>
                    <div className="text-sm text-neutral-900">{course.code}</div>
                    <div className="text-xs text-neutral-500">{course.name}</div>
                  </div>
                  <div className="flex gap-2">
                    {(['high', 'medium', 'low'] as const).map(level => (
                      <Button
                        key={level}
                        size="sm"
                        variant={interest === level ? 'default' : 'outline'}
                        className={interest === level ? getInterestColor(level) : ''}
                        onClick={() => setCourseInterests(prev => ({ ...prev, [course.code]: level }))}
                      >
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                      </Button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button size="lg" className="gap-2">
          <Save className="w-4 h-4" />
          Save Profile
        </Button>
      </div>
    </div>
  );
}
