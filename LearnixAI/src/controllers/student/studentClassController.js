const Assignment = require("../../models/teacherDashboard/assignmentModel");
const Announcement = require("../../models/teacherDashboard/announcementModel");
const StudyMaterial = require("../../models/teacherDashboard/studyMaterialModel");
const Subject = require("../../models/school/subjectModel");
const Submission = require("../../models/teacherDashboard/submissionModel");
const Class = require("../../models/school/classModel");
const mongoose = require("mongoose");
const Event = require("../../models/teacherDashboard/eventModel");
const StudentModel = require("../../models/student/studentModel");

// Get Student Class Dashboard
const getStudentClassDashboard = async (req, res) => {
    try {
        const { subjectId, emailId } = req.params;

        // Validate subject
        const subject = await Subject.findById(subjectId);
        if (!subject) {
            console.error(`Subject not found for ID: ${subjectId}`);
            return res.status(404).json({ message: "Subject not found." });
        }

        // Validate student
        const student = await StudentModel.findOne({ email: emailId });
        if (!student) {
            console.error(`Student not found for email: ${emailId}`);
            return res.status(404).json({ message: "Student not found." });
        }

        // Find class details
        const classData = await Class.findOne({
            schoolName: student.schoolName,
            studentDetails: { $elemMatch: { email: student.email } }
        });

        const classNumber = classData?.classNumber || "Unknown";
        const studentName = student.studentName;
        const { name: subjectName, teacherEmails } = subject;
        const teacherName = teacherEmails?.length ? teacherEmails[0].teacherName : "No Teacher Assigned";
        const formattedClassNumber = classNumber.replace(/\D/g, "");

        // Fetch content
        const announcements = await Announcement.find({
            classNumber: formattedClassNumber,
            subjectName: { $regex: new RegExp(`^${subjectName}$`, "i") }
        }).sort({ createdAt: -1 });

        const assignments = await Assignment.find({
            classNumber: formattedClassNumber,
            subject: { $regex: new RegExp(`^${subjectName}$`, "i") }
        }).sort({ createdAt: -1 });

        const studyMaterials = await StudyMaterial.find({
            classNumber: formattedClassNumber,
            subjectName: { $regex: new RegExp(`^${subjectName}$`, "i") }
        }).sort({ createdAt: -1 });

        const events = await Event.find({
            classNumber: formattedClassNumber,
            subjectName: { $regex: new RegExp(`^${subjectName}$`, "i") }
        }).sort({ dueDate: -1 });

        // Render view
        return res.render("student/classDashboard", {
            subjectId,
            subjectName,
            teacherName,
            announcements,
            assignments,
            studyMaterials,
            events,
            student
        });

    } catch (error) {
        console.error("Error fetching student class dashboard:", error);
        return res.status(500).json({ message: "Internal server error" });
    }
};

// Submit Assignment
const postAssignment = async (req, res) => {
    try {
        const { subjectId } = req.params;
        const studentEmail = req.body.email;

        if (!mongoose.Types.ObjectId.isValid(subjectId)) {
            return res.status(400).json({ message: "Invalid subject ID" });
        }

        const subject = await Subject.findById(subjectId);
        if (!subject) {
            return res.status(404).json({ message: "Subject not found" });
        }

        const { schoolName, classNumber } = subject;
        const classData = await Class.findOne({ schoolName, classNumber });
        if (!classData) {
            return res.status(404).json({ message: "Class not found" });
        }

        const student = classData.studentDetails.find(s => s.email === studentEmail);
        if (!student) {
            return res.status(404).json({ message: "Student not found in class" });
        }

        const studentName = student.studentName;
        const formattedClassNumber = classNumber.replace(/^Class\s*/i, '');

        if (!req.files || req.files.length === 0) {
            return res.status(400).json({ message: "No files uploaded" });
        }

        const submissionFiles = req.files.map(file => file.path);

        const newSubmission = new Submission({
            assignmentId: req.body.assignmentId,
            studentEmail,
            studentName,
            classNumber: formattedClassNumber,
            subject: subject.name,
            submissionFiles
        });

        await newSubmission.save();

        res.status(200).json({ message: "Assignment submitted successfully!" });

    } catch (error) {
        console.error("Error submitting assignment:", error);
        res.status(500).json({ message: "Error submitting assignment" });
    }
};

module.exports = {
    getStudentClassDashboard,
    postAssignment
};
